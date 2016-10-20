# Arista-VRRP-Route-Tracking
This Arista switch script allows you to track the availability of a route to influence the preference of VRRP. As of this creationg of this script Arista only have vrrp interface tracking. This script suppliments that by tracking the availability of a route in the routing table.

We have implementted this as checking for the existence of a default route, and then shutting down a vrrp tracked loopback interface to trigger the vrrp failover.

All of the config is in the initial variable setting of the script:
route = '0.0.0.0/0' # route to monitor
interface = 'Loopback100' # interface to monitor(needs to be the full interface name you see in show interface status)
interval = 0.1 # interval in seconds for how frequently to check the status


This requires VRRP interface tracking of a loopback interface which will be disabled by the script when the route disappears from the routing table. 

This requires unix API socket to be enabled on the device also, so the script can run commands on the switch:
management api http-commands
   protocol unix-socket

It's probably ideal to run this automatically at boot time of the switch.

event-handler vrrp-route-tracking
   trigger on-boot
   action bash sudo /mnt/flash/vrrp_route_tracking.py
   delay 120 #if you want it to wait for everything to load on the switch before starting it's checks and shutting interfaces(which might not be a bad idea to have some sort of startup delay for vrrp to not get traffic before the devices protocols are all up)
