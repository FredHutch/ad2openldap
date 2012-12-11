#!/usr/bin/env python
# requires python-ldap-2.3.x and won't work with 2.4.x

# Utility program to suck users and groups from AD and generate pseudo-LDIF 
# file for import into OpenLDAP.  As latter doesn't support nested groups,
# this program also hoists members of child groups into parent as necessary

import sys,ldap,getopt
from ldap.controls import SimplePagedResultsControl

from distutils import version
if version.StrictVersion(ldap.__version__)>=version.StrictVersion('2.4.0'):
   print "Error: this program requires python-ldap < 2.4.0!"
   sys.exit()

ad_acct="pickone@test.org"
ad_passwd="BadPenny"

def skip_split(s,split_char,skip_char):
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

def open_ldap(url,base,search_flt,page_size):
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

def ldap_paging(serverctrls,lc,l,page_size,base,search_flt):
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

# if field is present in crud, add to uid
def add_user_field(uid,field,crud):
   if field in crud:
      uid[field]=crud[field][0]

# returns list of users, dictionary of groups by users
def retrieve_ldap_userinfo(url,base,search_flt,acct_users,debug=0):
   page_size = 10

   l,lc,msgid=open_ldap(url,base,search_flt,page_size)

   users=[]
   name_dict={}
   pages = 0

   while True:
      pages += 1
      if debug:
         print "Getting page %d" % (pages,)
      rtype, rdata, rmsgid, serverctrls = l.result3(msgid)
      #print rdata

      for index,item in enumerate(rdata):
         #print index,type(item)
         uid={}
         for crud in list(item):
            if isinstance(crud,dict):
               #print crud

               for stuff in ['cn','uid','division','department','manager']:
                  add_user_field(uid,stuff,crud)

               if 'cn' in crud and 'uid' in crud:
                  name_dict[crud['cn'][0]]=uid['uid']

               if 'uid' in uid and (not acct_users or uid['uid'] in acct_users):
                  users.append(uid)

      if debug:
         print '%d results' % len(rdata)
         break
  
      msgid=ldap_paging(serverctrls,lc,l,page_size,base,search_flt)
      if msgid==0:
         break 

   return users,name_dict

def print_users(users,name_dict):
   for user in users:
      line=""
      for num,field in enumerate(['uid','division','department']):
         if num>0:
            line+=","
         if field in user:
            line+=user[field]

      line+="," 
      if 'manager' in user:
         manager_split=skip_split(user['manager'],',','\\')
         manager_cn=manager_split[0].split('=')[1]
         if manager_cn in name_dict:
            line+=name_dict[manager_cn]

      print line

def load_acct_users(filename):
   acct_users=[]
   try:
      with open(filename,'r') as f:
         for num,line in enumerate(f):
            if num>0:
               data=line.strip().split(',')
               acct_users.append(data[0])

   except IOError:
      print "Error: failed to open '"+filename+"'"

   return acct_users

def usage():
   print "ad-dump-users [options]"
   print "Options:"
   print "\t-a AD account"
   print "\t-A AD password"
   print "\t-S AD URL"
   print "\t-s AD base DN"
   print "\t-d destination LDAP base DN"

def main(argv):
   global ad_acct
   global ad_passwd

   ldap_url = "ldap://dc.test.org"
   src_base = "dc=test,dc=org"
   dst_base="dc=local"

   acct_users=[]

   try:
      opts,args=getopt.getopt(argv,"a:A:S:s:d:u:h")
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
      elif opt in ("-u"):
         acct_users=load_acct_users(arg)
   
   user_flt = r'(&(objectcategory=person)(objectclass=user))'
   users,name_dict=retrieve_ldap_userinfo(ldap_url,src_base,user_flt,
      acct_users) 

   users.sort(key=lambda uid: uid['uid'])

   print_users(users,name_dict)

   #print name_dict

if __name__=="__main__":
   main(sys.argv[1:])

