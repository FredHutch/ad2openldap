# Why ad2openldap ?

ad2openldap is a lightweight replicator for user, group and netgroup information
from Microsoft Active Directory into an OpenLDAP server. The original
version was developed at Fred Hutch in 2010 to overcome frustrations with slow
and unreliable Linux LDAP connectivity to Active Directory and to isolate badly
behaving HPC scripts ("fork bombs") from critical AD infrastructure.

## ad2openldap in 2018 and beyond

In 2017 we observed that newer solutions have grown in complexity (SSSD, Centrify)
but have not been able to match ad2openldap in performance and reliability (SSSD).
As ad2openldap continues to be a critical piece of infrastructure on more than
700 servers/compute nodes we decided to port the tool to Python3, add an easy
installer via pip3 and test it on newer OS. We hope it will be as useful to others
as it is to us.

## Installation

#### Ubuntu

On Ubuntu you will be prompted for an new LDAP Administrator password. please
remember this password.

    sudo apt install -y python3-pip slapd
    sudo pip3 install ad2openldap

#### RHEL/CentOS 6

    sudo yum -y install epel-release
    sudo yum -y install python34 python34-setuptools python34-devel gcc slapd
    sudo easy_install-3.4 pip
    sudo pip3 install ad2openldap

#### RHEL/CentOS 7

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

**execute the setup script and enter items when prompted**

    ad2openlap3 setup

then create a cronjob in file /etc/cron.d/ad2openldap that runs ca. every 15 min

    SHELL=/bin/bash
    MAILTO=alertemail@institute.org
    */15 * * * *   root /usr/local/bin/ad2openldap3 deltasync
       --dont-blame-ad2openldap -v >>/var/log/ad2openldap/ad2openldap.log 2>&1 ;
       /usr/local/bin/ad2openldap3 healthcheck -N username

## Background info and Troubleshooting

Initially ad2openldap worked by taking a complete dump of AD users/groups,
stopping OpenLDAP, emptying the database, and reloading all of it.  As that
made OpenLDAP unavailable (sometimes for extended periods) during updates, two
new methods were implemented.  First, a comparison is made between the current
AD dump and the last one, with only the changes being propagated to OpenLDAP
live.  Second, it's much faster to populate the OpenLDAP database by directly
constructing such a database from a template (LDIF file)
rather than incrementally deleting all and adding all.

To get started after installing the ad2openldap package, several settings
must first be configured in /etc/ad2openldap/ad2openldap.conf.  A note
on security, ad2openldap.conf must be 640 and root.openldap.

An update usually consists of three steps:

* Groups, users, and NIS netgroup entries are dumped from AD

* If a previous dump is present on the LDAP server, a comparison is made between
  the two updates.  If they differ, a list of LDAP server update transactions is
  generated.
* If an update is necessary due to changes from last time, the update
  transactions are entered into the local LDAP server.

On each LDAP server, the following tools are used:

* ad2openldap - update script invoked by cron via /etc/crontab

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


Troubleshooting:

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
