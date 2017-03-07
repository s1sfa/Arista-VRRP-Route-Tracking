#!/usr/bin/env python
import Logging,sys,os.path,socket
from jsonrpclib import Server
from jsonrpclib import history
from time import sleep
from xmlrpclib import ProtocolError as XML_ProtocolError

#initialization variables
switch = Server( "unix:/var/run//command-api.sock" )
positive_checks = 0
status = 'green'

#print output every interval to console if debug is specified at the command line
if len(sys.argv) > 1 and sys.argv[1].lower() == 'debug':
	debug = True
else:
	debug = False

##Variables to configure##
routes = [('0.0.0.0/0',4),('::/0',6)]        #route that is being tracked, when this route leaves the routing table the specified interface will be shutdown. This needs to be exactly the same as routing table entry.
interface = 'Loopback101'    #interface that is being tracked(needs to be the full name that you see under show interface. Example "show int lo100" first line shows "Loopback100")
interval = .1 #interval in seconds for how frequently to check the status

###Recovery Interval
intervals_to_recovery = 300    #how many intervals to wait for the route to be active to no shut the tracked interface, set to 0 to disable
recovery_time = intervals_to_recovery*interval

route_status = {}


Logging.logD( id="VRRP_ROUTE_TRACK",
              severity=Logging.logCritical,
              format="%s",
              explanation="Tracked route status change",
              recommendedAction=Logging.NO_ACTION_REQUIRED
)

def other_routes_status_red():
	for route,status in route_status.iteritems():
		if status.get('status') == 'red':
			return True
	return False

def socket_recovery():
    while True:
        sleep(interval)
        if os.path.exists('/var/run/command-api.sock'):
                Logging.log(VRRP_ROUTE_TRACK, "Socket has recovered to recover from socket error")
	        return Server( "unix:/var/run//command-api.sock" )

def recover():
    interface_recover = switch.runCmds(1, ['enable','configure','interface {}'.format(interface),'default shutdown','write memory'])[0]
    Logging.log(VRRP_ROUTE_TRACK, "Recovery: Tracked route {} has been in the routing table for {} seconds. Interface {} has been activated".format(route,recovery_time,interface))

def check_and_set_status(switch,status,positive_checks,route,version):
        if version == 6:
            ip_or_ipv6 = 'ipv6'
        elif version == 4:
            ip_or_ipv6 = 'ip'
        else:
            Logging.log(VRRP_ROUTE_TRACK, "IP version({}) invalid for {}".format(version,route))
            return 'unknown',0
        response,interface_status = switch.runCmds(1, ['show {} route {}'.format(ip_or_ipv6,route),'show interfaces {}'.format(interface)])
        if ip_or_ipv6 == 'ip':
            response = response['vrfs'].get('default')
        if route in response['routes'].keys():
            if interface_status['interfaces'][interface]['interfaceStatus'] != 'connected':
                #route exists but interface is still shutdown
                if status != 'yellow':
                    if status == 'red':
                        Logging.log(VRRP_ROUTE_TRACK, "Recovering: Route {} was found in the routing table, Interface {} is still shutdown".format(route,interface))
                    else:
                        Logging.log(VRRP_ROUTE_TRACK, "Route {} was found in the routing table, Interface {} is shutdown".format(route,interface))
                    status = 'yellow'
                #count positive checks incase we want todo do some sort auto recovery timer or notifications
                if route_status[route]['state'] == 'failed':
			positive_checks += 1
                if intervals_to_recovery != 0 and positive_checks > intervals_to_recovery:
			if other_routes_status_red() == False:
	                        recover()
			else:
				positive_checks = 0
            else:
            #Everything is good
                if status != 'green':
                    Logging.log(VRRP_ROUTE_TRACK, "Operational: Interface {} is up and route: {} is in routing table".format(interface,route))
                    status = 'green'
            return status,positive_checks
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
        return status,positive_checks

while True:
    try:
        for route_entry in routes:
            route,version = route_entry
            if route_status.get(route,False) == False:
               	route_status[route] = {}
		route_status[route]['status'] = 'green'
		route_status[route]['state'] = 'operational'
		route_status[route]['positive_checks'] = 0
            route_status[route]['status'],route_status[route]['positive_checks'] = check_and_set_status(switch,route_status[route]['status'],route_status[route]['positive_checks'],route,version)
            if route_status[route]['status'] == 'red':
		route_status[route]['state'] = 'failed'
	    elif route_status[route]['status'] == 'green':
               	route_status[route]['state'] = 'operational'
            if debug == True:
	            print route_status
            sleep(interval)
#clearing the command request and response history to avoid the history log running the switch out of memory
            history._instance.clear()
    except socket.error:
        #This socket error occurs during bootup of 7280 and maybe other switches, the /var/run/command-api.sock file seems to disappear temporarily. This exception will keep the program running until the file is back
        sleep(interval)
        Logging.log(VRRP_ROUTE_TRACK, "Program Failure: Trying to recover from socket error")
        switch = socket_recovery()
    except XML_ProtocolError:
	sleep(1)
	Logging.log(VRRP_ROUTE_TRACK, "Program failure: Trying to recover from XML Protocol Error")
	#error is generally ProtocolError for /var/run//command-api.sock/: 502 Bad Gateway, trying to catch the error and reinitialize the socket reference
	switch = Server( "unix:/var/run//command-api.sock" )
    except KeyboardInterrupt:
	Logging.log(VRRP_ROUTE_TRACK, "Keyboard Exit")
	break
    except:
        Logging.log(VRRP_ROUTE_TRACK,sys.exc_info())
        break
