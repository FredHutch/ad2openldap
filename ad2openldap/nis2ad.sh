#!/bin/bash

## This scipt only imports nisMap for autofs 
## and nisNetGroup for NFS exports but no
## users, groups or other NIS information
## it is intended for one time migration 
## from NIS to LDAP 

mydir="${0%/*}"
. ${mydir}/nis2ad.cfg

ldif_map=$(mktemp /tmp/ldif-map.XXX)
ldif_grp=$(mktemp /tmp/ldif-grp.XXX)

echo "writing ldif files ..."

# creating autofs ldif files
OU="OU=autofs,${LDAP_BASEDN}"
echo "dn: ${OU}" > $ldif_map
echo -e "objectClass: top\nobjectClass: organizationalUnit" >> $ldif_map
echo "" >> $ldif_map
echo "dn: CN=auto.master,${OU}" >> $ldif_map
echo -e "objectClass: top\nobjectClass: nisMap" >> $ldif_map
echo -e "nisMapName: auto.master\n" >> $ldif_map

tail --lines=+3 /etc/auto.master | while read line;  do
  mount=${line%% *}
  rest=${line#*:}
  map=${rest%% *}
  echo "dn: CN=${map},${OU}" >> $ldif_map
  echo -e "objectClass: top\nobjectClass: nisMap" >> $ldif_map
  echo "nisMapName: ${map}" >> $ldif_map
  echo "" >> $ldif_map
  echo "dn: CN=${mount}/,CN=auto.master,${OU}" >> $ldif_map
  echo -e "objectClass: top\nobjectClass: nisObject" >> $ldif_map
  echo "nisMapEntry: ${rest}" >> $ldif_map
  echo "nisMapName: auto.master" >> $ldif_map
  echo "" >> $ldif_map
  ypcat -k $map | while read entry; do
    key=${entry%% *}
    dir=${entry#* }
    echo "dn: CN=${key},CN=${map},${OU}" >> $ldif_map
    echo -e "objectClass: top\nobjectClass: nisObject" >> $ldif_map
    echo "nisMapEntry: ${dir}" >> $ldif_map
    echo "nisMapName: ${map}" >> $ldif_map
    echo "" >> $ldif_map
  done 
done
echo "ldif data written to: "
echo "$ldif_map"

# creating netgroup ldif files
OU="OU=netgroup,${LDAP_BASEDN}"
echo "dn: ${OU}" > $ldif_grp
echo -e "objectClass: top\nobjectClass: organizationalUnit" >> $ldif_grp
ypcat -k netgroup | while read line; do  
  ngroup=${line%% *}
  content=${line#* }
  if [[ -z ${ngroup} ]]; then 
    continue
  fi
  echo "" >> $ldif_grp  
  echo "dn: CN=${ngroup},${OU}" >> $ldif_grp
  echo -e "objectClass: top\nobjectClass: nisNetgroup" >> $ldif_grp  
  for entry in $content; do
    if [[ "$entry" =~ '(' ]]; then
      echo "nisNetgroupTriple: ${entry}" >> $ldif_grp
    else
      echo "memberNisNetgroup: ${entry}" >> $ldif_grp 
    fi
  done
done
echo "$ldif_grp"

echo "${LDAPADD} -x -h ${LDAPHOST} -D \"${LDAP_BINDDN}\" -w \"XXXXXXXX\" -f ${ldif_map} -f ${ldif_grp}"
read -p "Do you now want to import these ldif files to AD using this command line? " -n 1 -r -t 60
if [[ $REPLY =~ ^[Yy]$ ]]; then
  ${LDAPADD} -x -h ${LDAPHOST} -D "${LDAP_BINDDN}" -w "${LDAP_BINDCRED}" -f ${ldif_map} -f ${ldif_grp}
fi
echo ""
