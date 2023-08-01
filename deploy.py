#!/usr/bin/env python3

# IN THIS CODE, I WILL DEPLOY RAPID AND MECPerf IN THE SAME ENVIRONMENT -> Same as version v2 + gradle dependenices
import time
import logging
from apssh import (LocalNode, SshNode, SshJob, Run, RunString, RunScript, Service, Deferred, Capture, Variables, Push)
from apssh.formatters import  TimeHostFormatter #TimeHostFormatter
from asynciojobs import Job, Scheduler, PrintJob
from asyncssh.logging import set_log_level as asyncssh_set_log_level
from sys import platform
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path
from r2lab import ListOfChoices, ListOfChoicesNullReset, find_local_embedded_script



# include the set of utility scripts that are included by the r2lab kit
#INCLUDES = [find_local_embedded_script(x) for x in (
#    "r2labutils.sh", "nodes.sh", "mosaic-common.sh",
#)]

##########
default_gateway  = 'faraday.inria.fr'
default_slicename  = 'inria_rnis'

default_nodes = [1, 2, 5, 8]
default_node_core = 1
default_node_gnb = 2
default_node_mep = 5
default_node_rms = 8
default_quectel_nodes = [7]
default_phones = [1,]


default_verbose = False
default_dry_run = False

default_load_images = True
default_image = "ubuntu-22"
default_gnb_image = "gnuradio"
default_quectel_image = "quectel-mbim-single-dnn"
scripts = "./functions.sh"
##########

def fitname(node_id):
    """
    Return a valid hostname from a node number - either str or int
    """
    int_id = int(node_id)
    return "fit{:02d}".format(int_id)
def fitid(node_id):
    """
    Return a valid id from a node number - either str or int
    """
    int_id = int(node_id)
    return "{:02d}".format(int_id)
def run(*, gateway, slicename,
        nodes, node_core, node_gnb, quectel_nodes, phones,
        verbose, dry_run, load_images, node_image, gnb_image,quectel_image):
    """
    Launch latest OAICI 5G Core and gNB Docker images on R2lab

    Arguments:
        slicename: the Unix login name (slice name) to enter the gateway
        quectel_nodes: list of indices of quectel UE nodes to use
        phones: list of indices of phones to use
        nodes: a list of node ids to run the scenario on; strings or ints
                  are OK;
        node_epc: the node id on which to run the EPC
        node_enb: the node id for the enb, which is connected to B210/eNB-duplexer

    """

    quectel_ids = quectel_nodes[:]
    quectel = len(quectel_ids) > 0

    faraday = SshNode(hostname=default_gateway, username=slicename,
                      verbose=verbose,
                      formatter=TimeHostFormatter())

    core = SshNode(gateway=faraday, hostname=fitname(node_core),
                  username="root",
                  verbose=verbose,
                  formatter=TimeHostFormatter())
    
    gnb = SshNode(gateway=faraday, hostname=fitname(default_node_gnb),
                          username="root",
                          verbose=verbose,
                          formatter=TimeHostFormatter())
    mep = SshNode(gateway=faraday, hostname=fitname(default_node_mep),
                          username="root",
                          verbose=verbose,
                          formatter=TimeHostFormatter())
    rms = SshNode(gateway=faraday, hostname=fitname(default_node_rms),
                          username="root",
                          verbose=verbose,
                          formatter=TimeHostFormatter())

    node_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id),
                    username="root",formatter=TimeHostFormatter(),
                    verbose=verbose)
        for id in nodes
    }
    
    nodes_quectel_index = {
        id: SshNode(gateway=faraday, hostname=fitname(id),
                    username="root",formatter=TimeHostFormatter(),
                    verbose=verbose)
        for id in quectel_nodes
    }
    allnodes = nodes + quectel_nodes
    
    fit_core = fitname(node_core)
    fit_gnb = fitname(node_gnb)

    # the global scheduler
    scheduler = Scheduler(verbose=verbose)


    ##########
    check_lease = SshJob(
        scheduler=scheduler,
        node = faraday,
        critical = True,
        verbose=verbose,
        command = Run("rhubarbe leases --check"),
    )


    if load_images:
        green_light = [
            SshJob(
                scheduler=scheduler,
                required=check_lease,
                node=faraday,
                critical=True,
                verbose=verbose,
                label = f"Load image {default_image} on {fit_core, default_node_mep, default_node_rms }",
                commands=[
                    Run(f"rhubarbe load {fitid(node_core)} -i {default_image} -t 600"),
                    Run(f"rhubarbe load {default_node_mep} -i {default_image} -t 600"),
                    Run(f"rhubarbe load {default_node_rms} -i {default_image} -t 600"),
                    Run(f"rhubarbe wait {node_core}"),
                    Run(f"rhubarbe wait {default_node_mep}"),
                    Run(f"rhubarbe wait {default_node_rms}"),


                    #RunScript("oaici.sh", "init-epc", node_epc, node_enb), #REMOVE
                ]
            ),
            SshJob(
                scheduler=scheduler,
		        required=check_lease,
	            node=faraday,
                critical=True,
                verbose=verbose,
                label=f"Load image {default_gnb_image} on {fit_gnb}",
                 commands=[
                    Run(f"rhubarbe usrpoff {node_gnb}"), # if usrp is on, load could be problematic...
		            Run(f"rhubarbe load {node_gnb} -i {default_gnb_image}"),
                    Run(f"rhubarbe usrpon {node_gnb}"), 
		            Run(f"rhubarbe wait {node_gnb}"),

                    #RunScript("oaici.sh", "init-rapid", default_server_rapid),
                     ]
                ),

            SshJob(
                scheduler=scheduler,
                required=check_lease,
                node=faraday,
                critical=False,
                verbose=verbose,
                label="turning off unused nodes",
                command=[
                    Run("echo 'no node killed' ")
                ]
            )]
      
        ##########
        # Prepare the Quectel UE nodes
        if quectel:
            for id, node in nodes_quectel_index.items():
                print(id, node)
                prepare_quectel = SshJob(
                    scheduler=scheduler,
                    required=check_lease,
                    node=faraday,
                    critical=True,
                    verbose=verbose,
                    label = f"Load image {quectel_image} on quectel UE nodes",
                    commands=[
                        Run("rhubarbe", "usrpoff", id),
                        Run("rhubarbe", "load", id, "-i", quectel_image),
                        Run("sleep 20"),
                        Run("rhubarbe", "usrpon", id),
                        Run("sleep 20")]),
                init_quectel = SshJob(
                    scheduler=scheduler,
                    required=prepare_quectel,
                    node=node,
                    critical=True,
                    verbose=verbose,
                    label=f"Init Quectel UE on fit node {id}",
                    commands = Run("./init.sh")),
                sleep = SshJob(
                    scheduler=scheduler,
                    required=init_quectel,
                    node=faraday,
                    critical=True,
                    verbose=verbose,
                    command=Run("sleep 20"))
                check_stop_quectel = SshJob(
                    scheduler=scheduler,
                    required=sleep,
                    node=node,
                    critical=True,
                    verbose=verbose,
                    label=f"Check Quectel UE on fit node {id}",
                    commands = [
                         Run("./check-ue"),
                         Run("./stop.sh")]
                         )
    else:
        green_light = check_lease
        if quectel:
            for id, node in nodes_quectel_index.items():
                print(id, node)
                prepare_quectel = SshJob(
                    scheduler=scheduler,
                    required=check_lease,
                    node=faraday,
                    critical=True,
                    verbose=verbose,
                    label = f"Load image {quectel_image} on quectel UE nodes",
                    commands=[
                        Run("rhubarbe", "usrpoff", id),
                        Run("rhubarbe", "load", id, "-i", quectel_image),
                        Run("sleep 20"),
                        Run("rhubarbe", "usrpon", id),
                        Run("sleep 20")]),
                init_quectel = SshJob(
                    scheduler=scheduler,
                    required=prepare_quectel,
                    node=node,
                    critical=True,
                    verbose=verbose,
                    label=f"Init Quectel UE on fit node {id}",
                    commands = Run("./init.sh")),
                sleep = SshJob(
                    scheduler=scheduler,
                    required=init_quectel,
                    node=faraday,
                    critical=True,
                    verbose=verbose,
                    command=Run("sleep 20"))
                check_stop_quectel = SshJob(
                    scheduler=scheduler,
                    required=sleep,
                    node=node,
                    critical=True,
                    verbose=verbose,
                    label=f"Check Quectel UE on fit node {id}",
                    commands = [
                        Run("./check-ue"),
                        Run("./stop.sh")]
                        )
    

    start_nodes = [
        SshJob(
            scheduler=scheduler,
            required=green_light,
            node=core,
            critical=True,
            verbose=verbose,
            label = f"Launch Core and CM on {fit_core}",
            commands = [
                RunScript("core.sh"),
            ]),
        SshJob(
            scheduler=scheduler,
            required=green_light,
            node=gnb,
            critical=True,
            verbose=verbose,
            label = f"Launch RAN on {fit_gnb}",
            commands = [
                RunScript("ran.sh"),

            ]),
        SshJob(
            scheduler=scheduler,
            required=green_light,
            node=mep,
            critical=True,
            verbose=verbose,
            label = f"Launch MEP and RNIS on {fitname(default_node_mep)}",
            commands = [
                 RunScript("mep.sh"),
           ])
        ]
    
    '''set_nodes = [
        SshJob(
            scheduler=scheduler,
            required=start_nodes,
            node=core,
            critical=True,
            verbose=verbose,
            label = f"Set Core and CM on {fit_core}",
            commands = [
                #Run("cd blueprint/mep"),
                #Run("docker-compose -f docker-compose/docker-compose-core-network.yaml up -d"),
                #Run("docker-compose -f docker-compose/docker-compose-cm.yaml up -d"),
                RunScript("core.sh"),

            ]),
        SshJob(
            scheduler=scheduler,
            required=start_nodes,
            node=gnb,
            critical=True,
            verbose=verbose,
            label = f"Set RAN on {fit_gnb}",
            commands = [
                #Run("uhd_find_devices"),
                #Run("cd blueprint/mep"),
                #Run("docker-compose -f docker-compose/docker-compose-ran.yaml up -d oai-gnb oai-flexric rabbitmq"),
                #Run("docker-compose -f docker-compose/docker-compose-ran.yaml up -d oai-rnis-xapp"),
                RunScript("ran.sh"),

            ]),
        SshJob(
            scheduler=scheduler,
            required=start_nodes,
            node=mep,
            critical=True,
            verbose=verbose,
            label = f"Set MEP and RNIS on {fitname(default_node_mep)}",
            commands = [
                RunScript("mep.sh")
#                Run("cd blueprint/mep"),
#                Run("docker-compose -f docker-compose/docker-compose-mep.yaml up -d"),
#                Run("echo '192.168.70.2 oai-mep.org' >> /etc/hosts"),
#                Run("docker-compose -f docker-compose/docker-compose-rnis.yaml up -d"),                

            ])
        ]'''
    
    '''
    if quectel:
        for id, node in nodes_quectel_index.items():
            attach_quectel = SshJob(
                scheduler=scheduler,
                required=start_nodes,
                node=node,
                critical=True,
                verbose=verbose,
                label=f"Attach Quectel UE on fit node {id}",
                command = Run("./start.sh")),
            
   ''' 
        

  
    ##########
    # Update the .dot and .png file for illustration purposes
    scheduler.check_cycles()
    name = "deploy-oaici"
    print(10*'*', 'See main scheduler in',
          scheduler.export_as_pngfile(name))

    # orchestration scheduler jobs
    if verbose:
        scheduler.list()

    if dry_run:
        return True

    if not scheduler.orchestrate():
        print(f"RUN KO : {scheduler.why()}")
        scheduler.debrief()
        return False
    print(f"RUN OK, you can log now on the 5G Core node {fit_core} and the gNB node {fit_gnb} to check the logs")
    print(80*'*')

##########

def main():
    """
    Command-line frontend - offers primarily all options to oaici scenario

    """

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument("-g", "--gateway", default=default_gateway,
                        help="specify an alternate gateway")
    parser.add_argument("-s", "--slicename", default=default_slicename,
                        help="specify an alternate slicename")

    parser.add_argument("-N", "--node-id", dest='nodes', default=default_nodes,
                        choices=[str(x+1) for x in range(37)],
                        action=ListOfChoices,
                        help="specify as many node ids as you want,"
			" including master and eNB nodes")
    
    parser.add_argument("-R", "--ran", default=default_node_gnb, dest='node_gnb',
                        help="specify the id of the node that runs the gNodeB")
    
    parser.add_argument("-C", "--core", default=default_node_core, dest='node_core',
                        help="specify the id of the node that runs the 5G Core")

    parser.add_argument("-P", "--phones", dest='phones',
                        action=ListOfChoicesNullReset, type=int, choices=(1, 2, 0),
                        default=default_phones,
                        help='Commercial phones to use; use -p 0 to choose no phone')
    parser.add_argument("-Q", "--quectel-id", dest='quectel_nodes',
                        default=default_quectel_nodes,
                        choices=["7"],  # add others with sim in db
                        action=ListOfChoices,
			help="specify as many node ids with Quectel UEs as you want")

    parser.add_argument("-v", "--verbose", default=default_verbose,
                        action='store_true', dest='verbose',
                        help="run script in verbose mode")
    parser.add_argument("-d", "--debug", default=False,
                        action='store_true', dest='debug',
                        help="print out asyncssh INFO-level messages")
    parser.add_argument("-n", "--dry-runmode", default=default_dry_run,
                        action='store_true', dest='dry_run',
                        help="only pretend to run, don't do anything")

    parser.add_argument("-l", "--load-images", default=False, action='store_true',
                        help="use this for reloading images on used nodes;"
                             " unused nodes will be turned off")
    parser.add_argument("--image", dest="node_image",
                        default=default_image)
    parser.add_argument("--gnb-image", dest="gnb_image",
                        default=default_gnb_image)
    parser.add_argument("--quectel-image", dest="quectel_image",
                        default=default_quectel_image)

    args = parser.parse_args()

    # asyncssh info messages are turned on by default
    if not args.debug:
        asyncssh_set_log_level(logging.WARNING)
    del args.debug

    # we pass to run exactly the set of arguments known to parser
    # build a dictionary with all the values in the args
    kwds = args.__dict__.copy()

    # actually run it
    print(f"*** Deploy the latest OAICI docker images *** ")
    print("\tWith the following fit nodes:")
    for i in args.nodes:
        if i == args.node_core:
            role = "Core node"
        elif i == args.node_gnb:
            role = "gNB node"
        else:
            role = "Undefined"
        nodename = fitname(i)
        print(f"\t{nodename}: {role}")
    if args.phones:
        for phone in args.phones:
            print(f"Using phone{phone}")
    else:
        print("No phone involved")
    if args.quectel_nodes:
        for quectel in args.quectel_nodes:
            print(f"Using Quectel UE on node {quectel}")
    else:
        print("No Quectel UE involved")

    now = time.strftime("%H:%M:%S")
    print(f"Experiment STARTING at {now}")
    if not run(**kwds):
        print("exiting")
        return


##########
if __name__ == '__main__':
    # return something useful to your OS
    exit(0 if main() else 1)
