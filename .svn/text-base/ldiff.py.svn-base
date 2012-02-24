#!/usr/bin/env python

import sys,re,hashlib

def compute_hash(entry):
   m=hashlib.md5()
   for part in sorted(entry):
      m.update(part)
   return(m.digest())

def parse_ldif(ldif_filename):
   num_entries=0
   in_entry=0
   ldict={}

   p=re.compile('ou=(\S+)[,\n]')

   try:
      with open(ldif_filename,'r') as f:
         for line in f:
            line_s=line.strip()
            if in_entry==0:
               if len(line_s)>0:
                  in_entry=1
                  num_entries+=1
                  
                  entry=[line_s]
 
                  if line_s[0:3]=='dn:': 
                     dn=line_s.split(' ',1)[1]
                     ou=p.findall(dn)[0]
                     if ou not in ldict:
                        ldict[ou]={}

            else:
               if len(line_s)==0:
                  in_entry=0

                  if dn not in ldict[ou]:
                     ldict[ou][dn]=[compute_hash(entry),entry]
                  else:
                     print "Error: duplicate",dn,"in ou",ou

               else:
                  entry.append(line_s)

      # if still in entry at end
      if in_entry:
         if dn not in ldict[ou]:
            ldict[ou][dn]=[compute_hash(entry),entry]
         else:
            print "Error: duplicate DN",dn,"in OU",ou

   except IOError:
      print "Error: failed to open '"+ldif_filename+"'"

   print ldif_filename,"has",num_entries,"entries"
   return ldict

def write_entry(entry,changetype,stream):
   for num,item in enumerate(entry):
      print >>stream,item
      if num==0:
         print >>stream,"changetype:",changetype
         if changetype=="delete":
            break

   print >>stream

def usage():
   print "ldiff old.ldif new.ldif [output_ldif]"

def main(argv):
   num_args=len(argv)
   if num_args<2 or num_args>3:
      usage()
   else:
      old_ldif=parse_ldif(argv[0])
      new_ldif=parse_ldif(argv[1])

      if len(old_ldif)!=len(new_ldif):
         print "Number of OUs is different!"
         print "\told:",old_ldif.keys()
         print "\tnew:",new_ldif.keys()
      else:
         if num_args==3: # open output file
            stream=open(argv[2],'w')
         else:
            stream=sys.stdout

         # diff old against new for deletions     
         for ou_key,ou_value in old_ldif.iteritems():
            print "old",ou_key,len(old_ldif[ou_key])
            for key,value in ou_value.iteritems():
               if key not in new_ldif[ou_key]:
                  write_entry(value[1],"delete",stream)

         # diff new against old for adds and changes
         for ou_key,ou_value in new_ldif.iteritems():
            diffs=0
            print "new",ou_key,len(new_ldif[ou_key])
            for key,value in ou_value.iteritems():
               if key not in old_ldif[ou_key]:
                  write_entry(value[1],"add",stream)
               else:
                  if new_ldif[ou_key][key][0]!=old_ldif[ou_key][key][0]:
                     # easier to do modify as delete/add
                     write_entry(value[1],"delete",stream)
                     write_entry(value[1],"add",stream)
                     diffs+=1

            if diffs!=0:
               print "diffs",diffs

         if stream!=sys.stdout:
            stream.close()

if __name__=="__main__":
   main(sys.argv[1:])
