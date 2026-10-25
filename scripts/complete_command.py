#!/usr/bin/env python3
"""Read-only completion provider; cursor uses JS/DOM UTF-16 offsets. No UI injection."""
import argparse
import json
import sys
from js_command_bridge import _request

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('text',help='Full or partial @/$continuous-development input')
    cli.add_argument('--cursor',type=int,help='UTF-16 offset; default is end of input')
    args=cli.parse_args()
    try:
        result=_request(args.text,'complete',args.cursor)
    except ValueError as e:
        print(json.dumps({'error':str(e),'execution':'not_executed'},ensure_ascii=False));sys.exit(2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
