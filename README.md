# Arista-VRRP-Route-Tracking
This Arista switch script allows you to track the availability of a route to influence the preference of VRRP. As of the creation of this script, Arista only has vrrp interface tracking. This script suppliments that by tracking the availability of a route in the routing table.

If you are learning of a default route via a dynamic routing protocol, what happens to your traffic if that routing is down but your uplink interfaces are up on the VRRP master device? You will probably be dropping traffic until problem is fixed or someone intervenes to failover VRRP to the other device. With this script you can track the availability of a route(probably default route) which will trigger the vrrp failover.

####Switch Configuration requirements.
Configure an interface that vrrp will track, that the script can shutdown. I recommend a loopback interface.
Configuring the interface track object
Configure vrrp to track that interface tracking object.
Configure and run this script on the switch.

####All of the config is in the initial variable setting of the script:
```
route = '0.0.0.0/0' #route to monitor
interface = 'Loopback100' #interface to monitor(needs to be the full interface name you see in show interface status
interval = 0.1 #interval in seconds for how frequently to check the status
```

This requires VRRP interface tracking of a loopback interface which will be disabled by the script when the route disappears from the routing table. 

This requires unix API socket to be enabled on the device also, so the script can run commands on the switch:
```
management api http-commands
   protocol unix-socket 
```

It's probably ideal to run this automatically at boot time of the switch.

```
event-handler vrrp-route-tracking
   trigger on-boot
   action bash sudo /mnt/flash/vrrp_route_tracking.py
   delay 120 #if you want it to wait for everything to load on the switch before starting it's checks and shuttinginterfaces(which might not be a bad idea to have some sort of startup delay for vrrp to not get traffic before the devices protocols are all up)
```

####Auto Recovery
After x intervals the route has been in the routing table, enable the interface configured for tracking. 0 disables this autorecovery feature.

```
intervals_to_recovery = 0 #how many intervals to wait for the route to be active to no shut the tracked interface, set to 0 to disable
```
