#!/usr/bin/env python3
"""Synthetic stdio MCP server. Only two fixed probes and local evidence writes."""
import argparse
import json
from pathlib import Path
import sys


TOOLS = ('database_probe', 'echo_probe')


def serve(markers):
    markers.mkdir(parents=True, exist_ok=True)
    for line in sys.stdin:
        request = json.loads(line)
        if 'id' not in request:
            continue
        method = request.get('method')
        if method == 'initialize':
            result = {'protocolVersion': request.get('params', {}).get('protocolVersion', '2024-11-05'),
                      'capabilities': {'tools': {}},
                      'serverInfo': {'name': 'audit_fixture', 'version': '1.0.0'}}
        elif method == 'tools/list':
            result = {'tools': [
                {'name': name, 'description': 'Synthetic local probe; no database or network. Returns a fixed string and writes a local test marker.',
                 'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}
                for name in TOOLS]}
        elif method == 'tools/call':
            name = request.get('params', {}).get('name')
            if name not in TOOLS or request.get('params', {}).get('arguments', {}) != {}:
                print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32602, 'message': 'Only the two fixed probes with empty arguments are supported'}}), flush=True)
                continue
            with (markers / (name + '.jsonl')).open('a') as f:
                f.write(json.dumps({'tool': name, 'request_id': request['id']}) + '\n')
            result = {'content': [{'type': 'text', 'text': 'synthetic:' + name + ':ok'}]}
        elif method == 'ping':
            result = {}
        else:
            print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32601, 'message': 'Method not found'}}), flush=True)
            continue
        print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--markers', type=Path, required=True)
    serve(parser.parse_args().markers)
