# iplist-rsc v1
# resource=telegram
# generated=2026-01-30T17:33:11.266265Z
# count=6

:global AddressList
/ip/firewall/address-list add list=$AddressList address=91.108.4.0/22 comment="iplist:auto:telegram"
/ip/firewall/address-list add list=$AddressList address=91.108.8.0/22 comment="iplist:auto:telegram"
/ip/firewall/address-list add list=$AddressList address=91.108.56.0/22 comment="iplist:auto:telegram"
/ip/firewall/address-list add list=$AddressList address=95.161.64.0/20 comment="iplist:auto:telegram"
/ip/firewall/address-list add list=$AddressList address=149.154.160.0/22 comment="iplist:auto:telegram"
/ip/firewall/address-list add list=$AddressList address=149.154.164.0/22 comment="iplist:auto:telegram"
