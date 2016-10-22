#!/usr/bin/env python
import Logging
from jsonrpclib import Server
from time import sleep

#initialization variables
switch = Server( "unix:/var/run//command-api.sock" )
positive_checks = 0

##Variables to configure##
route = '0.0.0.0/0'		#route that is being tracked, when this route leaves the routing table the specified interface will be shutdown. 
interface = 'Loopback100'	#interface that is being tracked(needs to be the full name that you see under show interface. Example "show int lo100" first line shows "Loopback100")
interval = 0.1 #interval in seconds for how frequently to check the status

###Recovery Interval
intervals_to_recovery = 0	#how many intervals to wait for the route to be active to no shut the tracked interface, set to 0 to disable

Logging.logD( id="VRRP_ROUTE_TRACK",
              severity=Logging.logCritical,
              format="%s",
              explanation="Tracked route status change",
              recommendedAction=Logging.NO_ACTION_REQUIRED
)

recovery_time = intervals_to_recovery*interval
status = ''

def recover():
	interface_recover = switch.runCmds(1, ['enable','configure','interface {}'.format(interface),'default shutdown','write memory'])[0]
	Logging.log(VRRP_ROUTE_TRACK, "Recovery: Tracked route {} has been in the routing table for {} seconds. Interface {} has been activated".format(route,recovery_time,interface))

try:
    while True:
        sleep(interval)
        response,interface_status = switch.runCmds(1, ['show ip route {}'.format(route),'show interfaces {}'.format(interface)])
        if route in response['vrfs']['default']['routes'].keys():
       	    if interface_status['interfaces'][interface]['interfaceStatus'] != 'connected':
		#route exists but interface is still shutdown
                if status != 'yellow':
                    if status == 'red':
                        Logging.log(VRRP_ROUTE_TRACK, "Recovery: Route {} was found in the routing table, Interface {} is still shutdown".format(route,interface))
                    else:
                        Logging.log(VRRP_ROUTE_TRACK, "Route {} was found in the routing table, Interface {} is shutdown".format(route,interface))
                    status = 'yellow'
       	       	#count positive	checks incase we want todo do some sort	auto recovery timer or notifications
		positive_checks += 1
		if intervals_to_recovery != 0 and positive_checks > intervals_to_recovery:
			recover()
            else:
            #Everything is good
                if status != 'green':
                    Logging.log(VRRP_ROUTE_TRACK, "Interface: {} is up and route: {} is in routing table".format(interface,route))
                    status = 'green'
  	    continue
        #if route isn't found
        else:
            positive_checks = 0
       	    if interface_status['interfaces'][interface]['interfaceStatus'] == 'connected':
                if status != 'red':
                    interface_shutdown = switch.runCmds(1, ['enable','configure','interface {}'.format(interface),'shutdown','write memory'])[0]
                    Logging.log(VRRP_ROUTE_TRACK, "Failure: Shutdown Interface: {} because route {} was not found in routing table".format(interface,route))
                    status = 'red'
                else:
                    interface_shutdown = switch.runCmds(1, ['enable','configure','interface {}'.format(interface),'shutdown','write memory'])[0]
                    Logging.log(VRRP_ROUTE_TRACK, "Failure: Interface was enabled but route {} still doesn't exist in the routing table. Shutdown Interface {}".format(route,interface))
            else:
                ####Route doesn't exist and tracked interface is down
                if status != 'red':
                    Logging.log(VRRP_ROUTE_TRACK, "Failure: Interface {} and route {} are already down. But I did not shutdown the interface".format(interface,route))
                    status = 'red'
except:
    Logging.log(VRRP_ROUTE_TRACK, "Error occured: VRRP ROUTE CHECK is no longer running")
    exit(1)
