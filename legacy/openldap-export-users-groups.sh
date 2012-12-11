#!/bin/bash

# Script to dump list of groups and users from remote LDAP server and 
# feed list to ldapdelete for bulk deletion of server users & groups

TMPFILE=users-groups.ldif

if [ -z $1 ]
then
	echo "Usage: openldap-export-users-groups ldap_server [ldap_passwd][base_dn][bind_dn]"
	exit -1
else
	LDAPSERVER=$1
fi

if [ -z $2 ]
then
	LDAPPASSWD="pickone"
else
	LDAPPASSWD=$2
fi

if [ -z $3 ]
then
	BASEDN='dc=local'
else
	BASEDN=$3
fi

if [ -z $4 ]
then
	BINDDN='cn=Administrator,dc=local'
else
	BINDDN=$4
fi

echo "Retrieving groups"
ldapsearch -h $LDAPSERVER -x -L -b $BASEDN '(objectclass=posixGroup)' >$TMPFILE
echo "Retrieving users"
ldapsearch -h $LDAPSERVER -x -L -b $BASEDN '(objectclass=posixAccount)' >>$TMPFILE
