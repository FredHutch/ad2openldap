#!/bin/bash

SYNCROOT=/root/ldap

# Alert mailing list
MAILLIST=

TMPFILE=/tmp/ad-export.ldif
LASTTMPFILE=/tmp/ad-export.ldif.0
DIFFFILE=/tmp/ad-export-diff.ldif

LOCKFILE=/tmp/ldapsync.LOCK

LDAP_PASSWD="pickone"
LDAP_DN='cn=Administrator,dc=local'

DEFAULT_SHELL='-L /bin/bash'

TEMPLATE=$SYNCROOT/emptyldap.tar.bz2

if [ "$1" = "-full" -o "$1" = "--full" ]
then
	echo "Forcing full sync!"
	rm -f $TMPFILE $LASTTMPFILE $DIFFFILE
fi

touch $LOCKFILE

# if local LDIF file already exists, move to last
if [ -f $TMPFILE ]
then
	mv -f $TMPFILE $LASTTMPFILE
fi

# Dump AD users and groups to local LDIF file
$SYNCROOT/ad-export-users-groups.py $DEFAULT_SHELL >$TMPFILE
if [ $? -ne 0 ] ; then
	echo "Error in exporting from AD, exiting!"
        echo $HOSTNAME|mail -s 'AD Export Error in LDAP Update' $MAILLIST
	rm $LOCKFILE
	exit -1
fi

wc $TMPFILE

# check to see if there's really been a change
if [ -f $TMPFILE ] && [ -f $LASTTMPFILE ]
then
	$SYNCROOT/ldiff.py $LASTTMPFILE $TMPFILE $DIFFFILE
	if [ -s $DIFFFILE ]
	then
		ldapmodify -x -c -f $DIFFFILE -D $LDAP_DN -w $LDAP_PASSWD
		if [ $? -ne 0 ] ; then
			lds=`ldapsearch -h localhost -x -b 'dc=local' '(cn=cbenson)'|grep numEntries`
			if [ "$lds" == "# numEntries: 1" ];
			then
				echo $HOSTNAME|mail -s 'Modify Warning in LDAP Update - Server Up' $MAILLIST
			else
				echo $HOSTNAME|mail -s 'Modify Warning in LDAP Update - Server Down' $MAILLIST
			fi
		fi
	else
		echo "No difference in AD entities"
	fi

	rm $LOCKFILE
	exit 0
fi

# block remote access to LDAP server
eth=`ifconfig|head -1|cut -d ' ' -f 1`
echo "Blocking LDAP access to $eth"

iptables -A INPUT -i $eth -p tcp --dport 389 -j REJECT

if [ -f $TEMPLATE ]
then
	/etc/rc.d/ldap stop
        rm -f /var/lib/ldap/*
	echo "Installing $TEMPLATE into LDAP database directory"
	tar -jxf $TEMPLATE -C /var/lib/ldap
	echo "Quick loading $TMPFILE into LDAP database"
	slapadd -q -l $TMPFILE
	/etc/rc.d/ldap start
else
	# At this point, non-template based delete/restore should be history

	# Delete local users and groups
	$SYNCROOT/openldap-purge-users-groups.sh localhost
	if [ $? -ne 0 ] ; then
		echo "Error: purge from local LDAP. exiting with locked ports!"
	        echo $HOSTNAME|mail -s 'Purge Error in LDAP Update' $MAILLIST
		rm $LOCKFILE
		exit -1
	fi
	
	# Delete local users and groups again to ensure completion
	$SYNCROOT/openldap-purge-users-groups.sh localhost
	if [ $? -ne 0 ] ; then
		echo "Error: purge#2 from local LDAP. exiting with locked ports!"
		echo $HOSTNAME|mail -s 'Purge#2 Error in LDAP Update' $MAILLIST
		rm $LOCKFILE
		exit -1
	fi

	# Import LDIF file into local OpenLDAP server 
	ldapadd -x -c -f $TMPFILE -D $LDAP_DN -w $LDAP_PASSWD
	if [ $? -ne 0 ] ; then
		echo $HOSTNAME|mail -s 'Add Error in LDAP Update' $MAILLIST
	fi
fi

# enable remote access to LDAP server
iptables -D INPUT -i $eth -p tcp --dport 389 -j REJECT
echo "Opened LDAP access to $eth"
rm $LOCKFILE
