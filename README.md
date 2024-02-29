# vrf_epg_path_deployment
This is a raw script helping align ifConn with EGP/VRF/BD/Tenant info. 

# APIC Object Parser

## Capabilities

This standalone script is supposed to compose a single file (dictionary or CSV) where the tenant, VRF, BD, EPG and ifConn information will be aligned.  

This done by collect a number of objects directly from APIC. More specifically it polls fvRtCtx, fvRtBd and fvIfConn.

By selecting one of two options you can build a dictionary of the following format:

```bash
{
    "uni/tn-YOUR_TENANT/ctx-YOUR_VRF/rtctx-[uni/tn-YOUR_TENANT/BD-YOUR_BD]": [
        {
            "uni/tn-YOUR_TENANT/ap-YOUR_APP/epg-YOUR_EPG": [
                "node-XXX/dyatt-[topology/pod-X/protpaths-XXX-YYY/pathep-[intf]]/conndef/conn-[vlan-abc]-[0.0.0.0]",
            ]
        },
``` 
Or CSV file: 

```bash
Tenant,APP,VRF,BD,EPG,Node,Interface,Vlan,Intf_type
abl_tenant,my_AP,abl-vrf,my-bd,my-EPG1,123,esx03-vpc,2145,dynamic
...
```

## Instructions

Clone the repo

```bash
git clone https://github.com/ablusenkov/vrf_epg_path_deployment.git
```

(Optional) Create virtual environment in a way similar to:
```bash
cd vrf_epg_path_deployment
python3 -m venv venv
source venv/bin/activate
```

Install relations.

```bash
pip3 install -r requirements.txt
```

Run the script similar to: 

```bash
python3 ./vrf_epg_path_deployment.py --csv --apic apic_ip --usernam apic_usernam
 
```

See all options you have under: 
```bash
python vrf_epg_path_deployment.py --help
usage: vrf_epg_path_deployment.py [-h] -a APIC -u USERNAME [-o OUTPUT] [-c] [-d]
python              python3-config      python3.10          python3.10-intel64  python3.11-config   python3.8-config    
Compose VRF/EPG/etc data and stored under the <your_workdir_path_will_be_here>

options:
  -h, --help            show this help message and exit
  -a APIC, --apic APIC  Provide an IP/name of APIC
  -u USERNAME, --username USERNAME
                        Provide username
  -o OUTPUT, --output OUTPUT
                        Specify optional filename
  -c, --csv             Stores an outputs as a CSV file
  -d, --dict            Stores an outputs as a dictionary

```

Note also, that APIC address and USERNAME are mandatory parameters. Password asked to run API calls, but never stored outside of script working space.   

<h5 align="center">Author: <a href="https://github.com/ablusenkov">Oleksandr Blusenkov</a></h5>