#!/usr/bin/env python
# requires python-ldap-2.3.x and won't work with 2.4.x

# Utility program to suck users and groups from AD and generate pseudo-LDIF 
# file for import into OpenLDAP.  As latter doesn't support nested groups,
# this program also hoists members of child groups into parent as necessary

__app__ = "ad2openldap"
__ver__ = "1.5"
__ver_date__ = "2011-07-25" 
__author__ = "Jeff Katcher <jkatcher@fhcrc.org>"

import sys,ldap,getopt
from ldap.controls import SimplePagedResultsControl
import syslog

from distutils import version
if version.StrictVersion(ldap.__version__)>=version.StrictVersion('2.4.0'):
   print "Error: this program requires python-ldap < 2.4.0!"
   sys.exit()

ad_acct="pickone@test.org"
ad_passwd="BadPenny"

misc_attrs=['loginShell','gecos']

nobody=65534

default_page_size=500

# split LDAP-returned strings into components while editing out '\'s
def skip_split(s,split_char=',',skip_char='\\'):
   split=[]
   partial=""
   skip=0

   for c in s:
      if skip==1:
         partial+=c
         skip=0
      elif c==skip_char:
         skip=1
      elif c==split_char:
         split.append(partial)
         partial=""
      else:
         partial+=c

   # append residual partial if it exists
   if partial!="":
      split.append(partial)

   return split

# utility function to set dictionary attribute if possible
def print_attr(dict,attr):
   if attr in dict:
      print attr+":",dict[attr]

# iterates through users dictionary uses base as base dn
# if no gidNumber is set in AD, then 'nobody' value is set for export
def print_users(users,base,def_shell=""):
   #print "USERS",users
   for cn,user in users.items():
      #print "user",user
      if 'uid' not in user:
         print >>sys.stderr,"# Warning: no uid in",user
         continue
      if 'uidNumber' not in user:
         print >>sys.stderr,"# Warning: no uidNumber in",user
         continue
      print "dn: uid="+user['uid']+",ou=People,"+base
      print "cn:",user['uid']
      print "uid:",user['uid']
      print "objectclass: account"
      print "objectclass: posixAccount"
      print "uidnumber:",user['uidNumber']
      print "gidnumber:",
      if 'gidNumber' in user:
         print user['gidNumber']
      else:
         print nobody
      
      if 'unixHomeDirectory' in user:   
         print "homedirectory:",user['unixHomeDirectory']
      else:
         print "homedirectory: /home/"+user['uid']

      for attr in misc_attrs:
         print_attr(user,attr)

      if def_shell and 'loginShell' not in user:
         print "loginShell:",def_shell

      print

# convert member list to ldif syntax and print
def print_members(mlist,base):
   for user in mlist:
      print "member: uid="+user+",ou=people,"+base
      print "memberUid:",user

# output groups dictionary in LDIF format 
# skip groups ending in '-LS'
def print_groups(groups,group_gids,base,xgroups=[],debug=0):
   if debug:
      print "groups",len(groups)
      print "gids",len(group_gids)
   gintersect=0

   for group in groups.keys():
      if group in group_gids and group[-3:]!="-LS" and group not in xgroups:
         #print group,group_gids[group],groups[group]

         print "dn: cn="+group+",ou=group,"+base
         print "cn:",group
         print "objectclass: groupOfNames"
         print "objectclass: posixGroup"
         print "gidnumber:",group_gids[group]

         print_members(groups[group],base)

         print

         gintersect+=1

   if debug:
      print "gintersect",gintersect

# walk list of users and create username groups only if a user possesses a
# gidNumber equivalent to his uid.
def print_user_groups(users,base):
   for cn,user in users.items():
      if 'gidNumber' in user and user['gidNumber']==user['uidNumber']:
         print "dn: cn="+user['uid']+",ou=group,"+base
         print "cn:",user['uid']
         print "objectclass: groupOfNames"
         print "objectclass: posixGroup"
         print "gidnumber:",user['gidNumber']
         print "member: uid="+user['uid']+",ou=people,"+base
         print

# open connection to LDAP server, assuming paging necessary to complete 
# retrieval
def open_ldap(url,base,search_flt,page_size=default_page_size):
   ldap.set_option(ldap.OPT_REFERRALS, 0)
   l = ldap.initialize(url)
   l.protocol_version = 3
   l.simple_bind_s(ad_acct,ad_passwd)

   lc = SimplePagedResultsControl(
      ldap.LDAP_CONTROL_PAGE_OID,True,(page_size,'')
   )

   # Send search request
   msgid = l.search_ext(
     base,
     ldap.SCOPE_SUBTREE,
     search_flt,
     serverctrls=[lc]
   )

   return l,lc,msgid

# encapsulates LDAP paging mechanism, returning 0 if no more pages 
def ldap_paging(serverctrls,lc,l,base,search_flt,page_size=default_page_size):
   pctrls = [
      c
      for c in serverctrls
      if c.controlType == ldap.LDAP_CONTROL_PAGE_OID
   ]

   if pctrls:
      est, cookie = pctrls[0].controlValue
      if cookie:
         lc.controlValue = (page_size, cookie)
         msgid = l.search_ext(base, ldap.SCOPE_SUBTREE, search_flt,
                              serverctrls=[lc])
      else:
         return 0
   else:
      print "Warning: Server ignores RFC 2696 control."
      return 0

   return msgid

# generator encapulating paged ldap retrieval
def generate_ldap(url,base,search_flt,debug=0):
   l,lc,msgid=open_ldap(url,base,search_flt)

   pages = 0
   while True:
      pages += 1
      if debug:
         print "Getting page %d" % (pages,)
      rtype, rdata, rmsgid, serverctrls = l.result3(msgid)
      #print rdata
      for index,item in enumerate(rdata):
         #print index,type(item)
         for crud in list(item):
            #print type(crud),crud
            if isinstance(crud,dict):
               yield crud

      if debug:
         print '%d results' % len(rdata)
         break

      msgid=ldap_paging(serverctrls,lc,l,base,search_flt)
      if msgid==0:
         break 

# if field is present in crud, add to uid
def add_user_field(uid,field,crud):
   if field in crud:
      uid[field]=crud[field][0]

def generate_members(member_list):
   for name in member_list:
      for gname in skip_split(name):
         if gname[:3].lower()=="cn=":
            yield gname.split('=')[1]
            break

# returns list of users, dictionary of groups by users
def retrieve_ldap_userinfo(url,base,search_flt,debug=0):
   users={}
   groups={}

   for crud in generate_ldap(url,base,search_flt,debug):
      if 'uid' in crud:
         current_user=crud['uid'][0]
         if current_user in users:
            print >>sys.stderr,"# Warning: duplicate uid",current_user+"!"
         else:
            if 'memberOf' in crud:
               for gmember in generate_members(crud['memberOf']):
                  if gmember in groups:
                     groups[gmember].append(current_user)
                  else:
                     groups[gmember]=[current_user]

            uid={}

            uid['uid']=current_user

            if 'uidNumber' in crud:
               uid['uidNumber']=crud['uidNumber'][0]
            elif 'employeeID' in crud:
               uid['uidNumber']=crud['employeeID'][0]

            for attr in ['gidNumber','unixHomeDirectory']+misc_attrs:
               add_user_field(uid,attr,crud)

            users[current_user]=uid

   return users,groups

# returns dictionary of groups with members and gids 
# returns dictionary of all groups with members
def retrieve_ldap_groupinfo(url,base,search_flt,debug=0):
   # dictionary of gids by group name
   ggroups={}

   # dictionary of distinguishedNames and members by group name
   dgroups={}

   # list of exclusions from group 'ExcludedFromLDAPSync'
   xgroups=[]

   for crud in generate_ldap(url,base,search_flt,debug):
      if 'name' in crud and 'member' in crud:
         name=crud['name'][0]
         if 'gidNumber' in crud:
            ggroups[name]=crud['gidNumber'][0]

         if 'distinguishedName' in crud:
            dgroups[name]=[crud['distinguishedName'][0],crud['member']]

         # hardcode retrieval of this particular hack
         if name=="ExcludedFromLDAPSync":
            xgroups=[x for x in generate_members(crud['member'])]

   return ggroups,dgroups,xgroups

# confirms if all members of dn_list are substrings of group
def match_dn(dn_list,group):
   for dn in dn_list:
      if dn not in group:
         return False

   return True

# add user to parent_group if user is not already present
def add_user(cn,ugroups,parent_group,users):
   #print "adding",cn,"to",parent_group
   if cn in users and 'uid' in users[cn]:
      uid=users[cn]['uid']
      if uid not in ugroups[parent_group]:
         ugroups[parent_group].append(uid)
   #else:
   #   print "# Warning: uid is either nonexistent or empty for",cn

# iterate through members of group adding users to parent group
# if any members are themselves groups, recursively call on group
def flatten_group(group,groups,ugroups,parent_group,users):
   #print "depth",len(parent_group),"flattening",group
   for m in group[1]:
      # split dn into components removing '\ '
      #print "fg",m
      m_dn=skip_split(m)

      # extract cn from dn as group key
      cn=m_dn[0].split('=')[1]

      # if there's a group with this cn
      if cn in groups:
         current_group=groups[cn]

         # compare member dn components with group dn components
         # if child group is root parent group, abort due to infinite loop
         if match_dn(m_dn,current_group[0]) and cn not in parent_group:
            flatten_group(current_group,groups,ugroups,parent_group+[cn],users)
      else:
         add_user(cn,ugroups,parent_group[0],users)

# for each group with users
# check to see if any members are groups
# if so, get their members and add to parent
def flatten_groups(groups,ugroups,users):
   # for each group with users
   for g in ugroups.keys():
      #print "user group",g
      if g not in groups:
         print >>sys.stderr,"# Warning:",g,"in users but not in groups"
         continue
      
      # for each member in group 
      for m in groups[g][1]:
         # split dn into components removing '\ '
         m_dn=skip_split(m)

         # extract cn from dn as group key
         cn=m_dn[0].split('=')[1]

         # if there's a group with this cn
         if cn in groups:
            current_group=groups[cn]
            
            # compare member dn components with group dn components
            if match_dn(m_dn,current_group[0]):
               flatten_group(current_group,groups,ugroups,[g],users)

def print_ldap_list(crud,attr):
   if attr in crud:
      for item in crud[attr]:
         print attr+":",item

def retrieve_ldap_nisinfo(url,base,dst_base,search_flt,debug=0):
   lastmap=""
   auto_master=0

   for crud in generate_ldap(url,base,search_flt,debug):
      if 'nisNetgroup' in crud['objectClass']:
         if 'cn' in crud and 'nisNetgroupTriple' in crud:
            print "dn: cn="+crud['cn'][0]+",ou=netgroup,"+dst_base
            print_ldap_list(crud,'objectClass')
            #print "objectClass: nisNetgroup"
            print "cn:",crud['cn'][0]
            print_ldap_list(crud,'nisNetgroupTriple')
      else:
         cn=crud['cn'][0]
         if 'nisMap' in crud['objectClass']:
            print "dn: nisMapName="+cn+",ou=autofs,"+dst_base
            lastmap=",nisMapName="+cn
            if cn=="auto.master":
               auto_master+=1
               if auto_master>1:
                  syslog.syslog(LOG_WARNING,"Error: extra auto.master detected!")
         else:
            print "dn: cn="+cn+lastmap+",ou=autofs,"+dst_base
              
         for entry in ['objectClass','nisMapName','nisMapEntry']:
            print_ldap_list(crud,entry)

      print

# confirms if all members of dn_list are substrings of group
def usage():
   print "ad-export-users-groups [options]"
   print "Options:"
   print "\t-a AD account"
   print "\t-A AD password"
   print "\t-S AD URL"
   print "\t-s AD base DN"
   print "\t-d destination LDAP base DN"
   print "\t-L default shell if none set"

def main(argv):
   global ad_acct
   global ad_passwd

   ldap_url = "ldap://dc.test.org"
   src_base = "dc=test,dc=org"
   dst_base="dc=local"

   def_shell=""

   try:
      opts,args=getopt.getopt(argv,"a:A:S:s:d:L:h")
   except getopt.GetoptError:
      usage()
      sys.exit()

   for opt,arg in opts:
      if opt in ("-h"):
         usage()
         sys.exit()
      elif opt in ("-a"):
         ad_acct=arg
      elif opt in ("-A"):
         ad_passwd=arg
      elif opt in ("-S"):
         ldap_url=arg
      elif opt in ("-s"):
         src_base=arg
      elif opt in ("-d"):
         dst_base=arg
      elif opt in ("-L"):
         def_shell=arg

   nisinfo_flt = r'(|(objectClass=NisNetgroup)(objectClass=NisMap)(objectClass=NisObject))'
   retrieve_ldap_nisinfo(ldap_url,src_base,dst_base,nisinfo_flt)
   
   user_flt = r'(&(objectcategory=person)(objectclass=user))'
   users,users_by_group=retrieve_ldap_userinfo(ldap_url,src_base,user_flt) 

   group_flt = r'(objectClass=group)'
   group_gids,groups,xgroups=retrieve_ldap_groupinfo(ldap_url,src_base,group_flt) 
   flatten_groups(groups,users_by_group,users)

   # output users as LDIF
   print_users(users,dst_base,def_shell)

   # generate unique username groups if required as LDIF
   #print_user_groups(users,dst_base)

   # output groups as LDIF
   print_groups(users_by_group,group_gids,dst_base,xgroups)

if __name__=="__main__":
   main(sys.argv[1:])

