"""
The script helps putting some data around the VRFs/EPGs/nodes together.
In a nutshell, it creates an CSV file where VRF, BD, EPG, ifConn are aligned.
"""
import argparse
import csv
import json
import os
import re

import requests
import urllib3

from getpass import getpass


# Disabling an Insecure Request Warnings caused by self-signed Certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URI_AUTH = '/api/aaaLogin.json'
POST = 'post'
GET = 'get'

def auth_dict(apic_username, apic_password):
    """Constructs data block for authentication."""
    auth_body = {
        'aaaUser': {
            'attributes':
                {
                    'name': apic_username,
                    'pwd': apic_password
                }
            }
        }
    return auth_body


def call_apic(method, url, body=None, cookies=None):
    """Main API call function."""
    if method == GET:
        try:
            response = requests.get(
                url=url, json=body, cookies=cookies, verify=False)
        except requests.ConnectionError:
            return 'Some network error...'

    if method == POST:
        try:
            response = requests.post(
                url=url, json=body, cookies=None, verify=False)
        except requests.ConnectionError:
            return 'Some network error...'

    if response.status_code == 200:
        return response.json()
    return False, response.status_code


def decompose(key, data):
    """Decomposes lists to search an item. Returns result of re.search."""
    for item in data:
        result = re.search(key, item)
        if result:
            return result


def gen_dict_extract(var, key):
    """Function facilitating search in embedded dictionary."""
    if hasattr(var, 'items'):
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(v, key):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(d, key):
                        yield result


def url(uri):
    """Composes URI with APIC address."""
    apic_https = f'https://{apic_address}'
    return apic_https + uri


def mo_collect(token_raw):
    """Collects fvRtCtx, fvRtBd, fvIfConn MOs and
    returns corresponding lists."""
    if False in token_raw:
        print(token_raw[1])
    else:
        access_token = next(gen_dict_extract(token_raw, 'token'))
        token = {'APIC-cookie': access_token}
        uri_fvRtCtx = '/api/node/class/fvRtCtx.json'
        uri_fvRtBd = '/api/node/class/fvRtBd.json'
        uri_fvIfConn = '/api/node/class/fvIfConn.json'

        IfConn_list = []
        response_IfConn = call_apic(GET, url(uri_fvIfConn), cookies=token)
        for item in response_IfConn['imdata']:
            IfConn_list.append(next(gen_dict_extract(item, 'dn')))

        RtCtx_list = []
        response_RtCtx = call_apic(GET, url(uri_fvRtCtx), cookies=token)
        for item in response_RtCtx['imdata']:
            RtCtx_list.append(next(gen_dict_extract(item, 'dn')))

        RtBd_list = []
        response_RtBd = call_apic(GET, url(uri_fvRtBd), cookies=token)
        for item in response_RtBd['imdata']:
            RtBd_list.append(next(gen_dict_extract(item, 'dn')))

    return IfConn_list, RtCtx_list, RtBd_list


def main_parser(IfConn_list, RtCtx_list, RtBd_list):
    """Following routine decomposes fvIfConn objects in a dictionary where
    the key is the reference to epg path and value is a list of stpathatt,
    dyatt objects here and below `(stpathatt|dyatt).*` is used to exclude
    attEntitypathatt which represents scenario with
    VMM+resolution `Pre-provision` or Static EPGs under the AEP."""

    search_key = (
        r'\[(uni/(tn-.*)/ap.*(epg-.*))\]/(node-\d+/(stpathatt|dyatt).*)')

    epg_ifconn_dict = {}
    for item in IfConn_list:
        epg_result = re.search(search_key, item)
        if epg_result:
            v1 = epg_result.group(1)
            if v1 in epg_ifconn_dict:
                if isinstance(epg_ifconn_dict[v1], list):
                    epg_ifconn_dict[v1].append(epg_result.group(4))
            else:
                epg_ifconn_dict[v1] = [epg_result.group(4)]

    # Takes keys of the previous dictionary
    # to find a reference in the RtCtx_list over RtBd_list
    final_dict = {}
    for v1, k1 in epg_ifconn_dict.items():
        search_key = fr'(uni/.*)/rtbd-\[{v1}\]'
        bd_result = decompose(search_key, RtBd_list)
        if bd_result:
            v2 = bd_result.group(1)
            key = fr'.*{v2}\]'
            result = decompose(key, RtCtx_list).group()

            if final_dict.get(result):
                final_dict[result].append({v1: k1})
            else:
                final_dict[result] = [{v1: k1}]

    return final_dict


def dict_create(filename, data):
    """Writes a readable dictionary."""
    with open(filename, 'w') as fp:
        json.dump(data, fp, indent=4)


def csv_create(filename, data):
    """Fetches the values in question and creates a CVS file."""
    with open(filename, 'w', newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(
            ['Tenant', 'APP', 'VRF', 'BD', 'EPG', 'Node',
             'Interface', 'Vlan', "Intf_type"])

        for key, values in data.items():
            search_key = r'tn-(.*)/ctx-(.*)/rtctx.*/BD-(.*)]'
            result = re.search(search_key, key)
            tenant = result.group(1)
            vrf = result.group(2)
            bd = result.group(3)

            for value in values:
                for key_inner, value_inner in value.items():
                    search_key = r'/ap-(.*)/epg-(.*)'
                    result = re.search(search_key, key_inner)
                    app = result.group(1)
                    epg = result.group(2)
                    for value in value_inner:
                        search_key = (
                            r'node-(.*)/(stpathatt-\[(.*)\]/.*\[vlan-(.*)\]-)|'
                            r'node-(.*)/(dyatt-.*pathep-\[(.*)\]].*\[vlan-'
                            r'(.*)\]-)'
                        )
                        result = re.search(search_key, value)
                        if result:
                            if result.group(1):
                                node = result.group(1)
                                interface = result.group(3)
                                vlan = result.group(4)
                                writer.writerow(
                                    [tenant, app, vrf, bd, epg, node,
                                     interface, vlan, 'static'])
                            if result.group(5):
                                node = result.group(5)
                                interface = result.group(7)
                                vlan = result.group(8)
                                writer.writerow(
                                    [tenant, app, vrf, bd, epg, node,
                                     interface, vlan, 'dynamic'])



if __name__ == '__main__':
    working_directory = os.getcwd()
    parser = argparse.ArgumentParser(
        description=f'Compose VRF/EPG/etc data and stored under the {working_directory}')
    parser.add_argument('-a', '--apic', required=True,
                        help='Provide an IP/name of APIC')
    parser.add_argument('-u', '--username', required=True,
                        help='Provide username')
    parser.add_argument('-o', '--output', type=str,
                        help='Specify optional filename')
    parser.add_argument('-c', '--csv', action='store_true',
                        help='Stores an outputs as a CSV file')
    parser.add_argument('-d', '--dict', action='store_true',
                        help='Stores an outputs as a dictionary')
    args = parser.parse_args()

    apic_address = args.apic
    apic_username = args.username
    apic_password = str(getpass('Password (will not be echoed or stored): '))

    fullpath = ''
    if args.output:
        fullpath = working_directory + '/' + args.output
        print(f'Your file should be stored as {fullpath}')

    # retrieve an access token and build a cookies used for further API calls
    auth_body = auth_dict(apic_username, apic_password)

    access_reply = call_apic(POST, url(URI_AUTH), auth_body)
    if isinstance(access_reply, dict):
        IfConn_list, RtCtx_list, RtBd_list = mo_collect(access_reply)
        final_dict = main_parser(IfConn_list, RtCtx_list, RtBd_list)
        if args.dict:
            if not args.output:
                fullpath = working_directory + '/vrf_epf_path_dep.txt'
            dict_create(fullpath, final_dict)
            print(f'Dict file is now saved under the {fullpath}')

        if args.csv:
            if not args.output:
                fullpath = working_directory + '/vrf_epf_path_dep.csv'
            csv_create(fullpath, final_dict)
            print(f'CSV file is now saved under the {fullpath}')

    else:
        print(f'Something went wrong. '
              f'An API call failed with {access_reply[1]} code.')

