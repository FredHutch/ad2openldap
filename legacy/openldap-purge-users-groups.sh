#!/bin/bash

# Script to dump list of groups and users from remote LDAP server and 
# feed list to ldapdelete for bulk deletion of server users & groups
#
# Post the introduction of the far superior templated way of doing this
# This code should be only of historical interest.

TMPFILE=/tmp/ol-u-g.tmp

if [ -z $1 ]
then
	echo "Usage: openldap-purge-users-groups ldap_server [ldap_passwd][base_dn][bind_dn]"
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

echo "Retrieving groups and users"
ldapsearch -h $LDAPSERVER -x -b $BASEDN '(|(objectclass=posixGroup)(objectclass=posixAccount))'|/root/ldap/dnext >$TMPFILE
if [ $? -eq 0 ] ; then
	echo "Retrieving NIS entities"
	ldapsearch -h $LDAPSERVER -x -b $BASEDN '(objectclass=nisNetgroup)'|grep "dn:"|sed 's/dn: //' >>$TMPFILE
	ldapsearch -h $LDAPSERVER -x -b $BASEDN '(objectclass=nisObject)'|grep "dn:"|sed 's/dn: //' >>$TMPFILE
	ldapsearch -h $LDAPSERVER -x -b $BASEDN '(objectclass=nisMap)'|grep "dn:"|sed 's/dn: //' >>$TMPFILE
	echo "Deleting groups, users and NIS entities"
	wc $TMPFILE
	ldapdelete -h $LDAPSERVER -D $BINDDN -w $LDAPPASSWD -f $TMPFILE
	if [ $? -ne 0 ] ; then
		exit $?
	fi
else
	exit $?
fi
rm -f $TMPFILE
