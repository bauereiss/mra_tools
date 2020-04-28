#!/usr/bin/env python3

'''
Convert ArchEx instruction tag file to ASLi instruction definitions
'''

import argparse
import glob
import json
import os
import re
import string
import sys
from collections import defaultdict
from itertools import takewhile

from asl_utils import *

########################################################################
# Tagfiles
########################################################################

def readTagFile(fns, ignores, defines):
    '''
    Read a TAGS file and split it into a dictionary
    indexed by the tag label
    '''
    tags = dict()
    for fn in fns:
        with open(fn, "r") as f:
            content = f.readlines()

        label = None
        body = []
        ifdef_ignore = False
        for l in content:
            l = l.rstrip()
            if l.startswith("TAG:"):
                if label is not None: tags[label] = body
                label = l[4:]
                body = []
                ifdef_ignore = False
            elif l.startswith("#ifdef") or l.startswith("#if defined"):
                idx = 6 if l.startswith("#ifdef") else 11
                const = l[idx:].strip()
                const = const.strip("()")
                if (const+"=0") in defines:
                    ifdef_ignore = True
                elif not (const in defines or (const+"=1" in defines)):
                    print (const)
                    print ("Warning: " + l + " (ignoring until #else or #endif)")
            elif l.startswith("#if "):
                print("Warning: " + l + " (ignoring until #else or #endif)")
                ifdef_ignore = True
            elif l.startswith("#else"):
                ifdef_ignore = not ifdef_ignore
            elif l.startswith("#endif"):
                ifdef_ignore = False
            elif l in ignores or ifdef_ignore or l.startswith("#"):
                continue
            elif l == '' and (body == [] or body[-1].rstrip() == ''):
                continue
            else:
                body.append(l)

        if label is not None: tags[label] = body
        label = None

    return tags

########################################################################
# readIndex
########################################################################

def readIndex(ls):
    decs = []
    post = None
    exec = None
    for l in ls:
        if l == "":
            continue
        (p,q) = l.split()
        if p == "Execute:":
            exec = q
        elif p == "Decode:":
            (r,s) = q.split("@")
            decs.append((r,s))
        elif p == "Postdecode:":
            post = q
    return (decs, post, exec)

def checkIndex(idx, tags):
    (decs, post, exec) = idx
    checked_decs = []
    for (dec, diag) in decs:
        if not (dec in tags):
            print("Warning: Missing decode " + dec)
        elif not (diag in tags):
            print("Warning: Missing diagram " + diag)
        else:
            checked_decs.append((dec, diag))
    if post and not (post in tags):
        print("Warning: Missing postdecode " + post)
        post = None
    if exec and not (exec in tags):
        print("Warning: Missing execute " + exec)
        exec = None
    return (checked_decs, post, exec)

########################################################################
# readDiagram
########################################################################

def readDiagram(d, nm):
    isa = d[0]
    width = 16 if isa == "T16" else 32
    mask = list('y'*width)
    fields = {}
    unpreds = []
    d = d[1:]
    lastidx = width
    # For T32, fields might be given for two half-words separately
    # (both with indices in 15..0)
    hw1 = True if isa == "T32" else False
    for l in d:
        l = re.sub(r'\s*//.*', "", l)
        l = re.sub(r'\s+', " ", l)
        if len(l) == 0:
            continue
        bits = l.split(" ")
        if len(bits) == 0:
            continue
        loc = bits[0]
        m1 = re.match('([0-9]+)$', loc)
        m2 = re.match('([0-9]+):([0-9]+)$', loc)
        if m1:
            (hi,lo) = (int(loc), int(loc))
        elif m2:
            (hi, lo) = (int(m2.group(1)), int(m2.group(2)))
        else:
            print("Unable to parse "+loc)
            exit(1)
        wd = hi - lo + 1

        if hw1 and hi > lastidx:
            hw1 = False

        lastidx = lo

        if hw1 and lo < 16:
            lo = lo + 16
            hi = hi + 16

        if len(bits) == 2 and re.match("[01x!()]+$", bits[1]):
            name    = '_'
            content = bits[1]
        elif len(bits) == 3 and re.match("[01x!()]+$", bits[2]):
            name    = bits[1]
            content = bits[2]
        elif len(bits) == 2:
            name    = bits[1]
            content = 'x' * wd
        else:
            print("Unable to parse "+str(bits))
            exit(1)

        content = content.replace("!0", "x").replace("!1", "x")
        data = list(content.replace("(","").replace(")",""))
        assert(len(data) == wd)

        if name != "_": fields[name] = (lo, wd)

        data.reverse()
        mask[lo:hi+1] = data

        unps = content.replace("(1)","O").replace("(0)","Z")
        for i,b in enumerate(list(unps)):
            if b == "O":
                unpreds.append((lo+i, 1))
            elif b == "Z":
                unpreds.append((lo+i, 0))

        # print(f"{isa} {lo}+:{wd} {name} {content}")
    mask.reverse()
    mask = ''.join(mask)
    if 'y' in mask: # check every bit of opcode is described
        print ("Missing opcode bits for " + nm + ": " + mask)
        exit(1)

    guard = "cond != '1111'" if "cond" in fields else "TRUE"

    return (isa, mask, unpreds, fields, guard)

########################################################################
# patchIdents
########################################################################

def patchIdent(x):
    x = x.replace("/", "_")
    x = x.replace(".", "_")
    x = x.replace("-", "_")
    x = x.replace(":", "_")
    return x

########################################################################
# writeASL
########################################################################

def writeASL(f, tags):
    ind = ' '*4 # indentation string
    #for l in tags['notice:asl']:
    #    print(l, file=f)
    for (label, body) in tags.items():
        if label.endswith(":index"):
            nm = label.replace(":index","")
            (decs, post, exec) = checkIndex(readIndex(body), tags)
            if decs == [] or not exec:
                continue
            exec_code = []
            if exec in tags:
                exec_code = tags[exec]
            else:
                print("Warning: Execute clause " + exec + " missing")
            (tops, conditional, decode_top, exec_code) = demangleExecuteASL(exec_code)
            print(file=f)
            if tops:
                print(tops, file=f)
                print(file=f)
            print("__instruction "+patchIdent(nm), file=f)
            for (decode, diag) in decs:
                nm = diag.replace(":diagram","")
                if diag in tags:
                    diagram = tags[diag]
                    (isa, mask, unpreds, fields, guard) = readDiagram(diagram, nm)
                    print(ind+'__encoding '+patchIdent(nm), file=f)
                    print(ind*2+'__instruction_set '+isa, file=f)
                    for (name, (lo, wd)) in fields.items():
                        print(ind*2+'__field '+name+' '+str(lo)+'+:'+str(wd), file=f)
                    print(ind*2+'__opcode '+"'"+mask+"'", file=f)
                    print(ind*2+'__guard '+guard, file=f)
                    for (ix, v) in unpreds:
                        print(ind*2+'__unpredictable_unless '+str(ix)+" == '"+str(v)+"'", file=f)
                    print(ind*2+'__decode', file=f)
                    if decode in tags:
                        decode_tops = (decode_top.splitlines() if decode_top else [])
                        for l in (decode_tops + tags[decode]):
                            print(ind*3+l, file=f)
                    else:
                        print("Warning: Decoder " + decode + " missing")
                    print(file=f)

            if post:
                print(ind+'__postdecode', file=f)
                if post in tags:
                    for l in tags[post]:
                        print(ind*2+l, file=f)
                else:
                    print("Warning: Postdecoder " + post + " missing")
                print(file=f)

            print(ind+'__execute'+(' __conditional' if conditional else ''), file=f)
            for l in exec_code:
                print(ind*2+l, file=f)
            print(file=f)


########################################################################
# Main
########################################################################

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-v', '--verbose', help='Use verbose output',
                        action = 'count', default=0)
    parser.add_argument('-o', '--output',  help='File to store tag output',
                        metavar='FILE', default='output')
    parser.add_argument('-I', '--ignores-file', help='File with lines to ignore',
                        metavar='FILE', dest='ignores')
    parser.add_argument('-D', help='Define constant',
                        metavar='CONST[=0|1]', dest='defines', action='append', default=[])
    parser.add_argument('input', metavar='<file>',  nargs='+',
                        help='input file')
    args = parser.parse_args()

    ignores = []
    if args.ignores:
        with open(args.ignores, "r") as f:
            ignores = [l.rstrip() for l in f.readlines() if l.strip() != '']

    tags = readTagFile(args.input, set(ignores), set(args.defines))

    with open(args.output, "w") as f:
        writeASL(f, tags)
    return

if __name__ == "__main__":
    sys.exit(main())

########################################################################
# End
########################################################################

