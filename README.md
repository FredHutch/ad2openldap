# ad2openldap - IDMAP for Linux replicated from AD  

## Why ad2openldap ?

ad2openldap is a lightweight replicator for user, group and netgroup information
from Microsoft Active Directory into an OpenLDAP server to serve as Unix IDMAP
solution. The original version was developed at Fred Hutch in 2010 to overcome
frustrations with slow and unreliable Linux LDAP connectivity to Active Directory
and to isolate badly behaving HPC scripts ("fork bombs") from critical AD
infrastructure.

## ad2openldap in 2018 and beyond

In 2017 we observed that newer solutions have grown in complexity (SSSD, Centrify)
but have not been able to match ad2openldap in performance and reliability (SSSD).
As we are migrating more services to cloud we continue to benefit from LDAP
caches/replicas that provide low latency ldap services and ad2openldap continues
to be a critical piece of infrastructure on more than 2000 servers/compute nodes
on premise and in AWS and Google cloud.
We decided to port the tool to Python3, add an easy installer via pip3 and test
it on newer OS. We hope it will be as useful to others as it is to us.

## Installation

#### Ubuntu

On Ubuntu you will be prompted for an new LDAP Administrator password. please
remember this password.

    sudo apt install -y python3-pip slapd
    sudo pip3 install ad2openldap

#### RHEL/CentOS 6 (untested in 2018)

    sudo yum -y install epel-release
    sudo yum -y install python34 python34-setuptools python34-devel gcc slapd
    sudo easy_install-3.4 pip
    sudo pip3 install ad2openldap

#### RHEL/CentOS 7 (untested in 2018)

    sudo yum -y install python??
    sudo pip3 install ad2openldap

## Configuration

/etc/ad2openldap/ad2openldap.conf requires these minimum settings:

    # openldap adimistrator password (you set this during installation)
    bind_dn_password: ChangeThisLocalAdminPassword12345
    # AD service account (userPrincipalName aka UPN)
    ad_account: ldap@example.com
    # password for AD service account
    ad_account_password: ChangeThisPassword
    # AD LDAP URL of one of your domain controllers
    ad_url: ldap://dc.example.com
    # The base DN to use from Active Directory, under which objects are  retrieved.
    ad_base_dn: dc=example,dc=com

execute the setup script and enter items when prompted

    ad2openlap3 setup

then create a cronjob in file /etc/cron.d/ad2openldap that runs ca. every 15 min

    SHELL=/bin/bash
    MAILTO=alertemail@institute.org
    */15 * * * *   root /usr/local/bin/ad2openldap3 deltasync
       --dont-blame-ad2openldap -v >>/var/log/ad2openldap/ad2openldap.log 2>&1 ;
       /usr/local/bin/ad2openldap3 healthcheck -N username

It is strongly recommended to up the default open files limit for slapd to at least 8192

    echo “ulimit -n 8192” >> /etc/default/slapd (or /etc/defaults/slapd depending on distribution)

## Troubleshooting

Use the --verbose flag to log to STDOUT/STDERR.

The AD dumps and diffs are in /tmp by default:

    ad_export.ldif - current dump
    ad_export.ldif.0 - last dump
    ad_export_delta.diff - computed differences between these files

Possible failure modes are:

LDAP server failure - needs restart, possibly followed by forced full update
if corrupt or incomplete

Firewall block still improperly active - look at update script for removal
syntax (this failure is very unlikely given the current process)

Bad or conflicting AD entities - a forced full update should remedy this

In the event that an incremental update is not possible or bypassed using the
command line parameter '--fullsync', a full update will instead occur.

A full update:

* Dumps groups, users and NIS group entities from AD
* Locks out remote access to the LDAP server via the firewall
* Shuts down the LDAP server
* Writes a new blank database using the LDIF template
* Directly imports AD dump into database
* Restarts LDAP server
* Removes firewall block on LDAP server


## Extra: NIS -> AD migration

Migrating NIS netgroups and autofs maps to LDAP can result in cumbersome
management as one has to give up the convenience of editing flat files.
However managing fewer servers is also nice and you may want to migrate
anyway.  
Most people seem to be recommending these tools: 
http://www.padl.com/download/MigrationTools.tgz

We were not able to get them to work in 2019 and replaced them with `nis2ad.sh`.

`nis2ad.sh` is a simple shell script that uses the environment variables of
the PADL tools, please edit nis2ad.cfg

```
export LDAPHOST='dc.my.org'
export LDAP_BASEDN='OU=NIS,DC=my,DC=org'
export LDAP_BINDDN='CN=myserviceaccount,OU=Users,DC=my,DC=org'
export LDAP_BINDCRED='myserviceaccount_password'
export LDAPADD='/usr/bin/ldapadd'
export LDAPMODIFY='/usr/bin/ldapmodify'
```