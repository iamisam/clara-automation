from flask import Flask, request, jsonify
import subprocess
import json
import os
from pathlib import Path
import uuid

app = Flask(__name__)

def discover_files(dataset_path="/home/isam/clara-automation/dataset"):
    """Auto-discover all processable files"""
    calls = []
    
    demo_path = Path(dataset_path) / "demo"
    onboarding_path = Path(dataset_path) / "onboarding"
    
    if demo_path.exists():
        for folder in demo_path.iterdir():
            if folder.is_dir():
                account_id = folder.name
                for file in folder.rglob('*'):
                    if file.is_file() and file.suffix.lower() in ['.txt', '.m4a', '.mp4', '.mp3', '.wav', '.md']:
                        calls.append({
                            "type": "demo",
                            "file": str(file.relative_to("/home/isam/clara-automation")),
                            "account_id": account_id
                        })
    
    if onboarding_path.exists():
        for folder in onboarding_path.iterdir():
            if folder.is_dir():
                account_id = folder.name
                for file in folder.rglob('*'):
                    if file.is_file() and file.suffix.lower() in ['.txt', '.m4a', '.mp4', '.mp3', '.wav', '.md']:
                        calls.append({
                            "type": "onboarding",
                            "file": str(file.relative_to("/home/isam/clara-automation")),
                            "account_id": account_id
                        })
    
    return calls

@app.route('/discover', methods=['GET'])
def discover():
    """Returns all discovered files"""
    calls = discover_files()
    return jsonify({"calls": calls, "total": len(calls)})

@app.route('/process', methods=['POST'])
def process():
    """Process single call"""
    data = request.json
    
    account = data.get('account_id')
    version = 'v1' if data['type'] == 'demo' else 'v2'
    
    cmd = [
        'uv', 'run', 'python', 
        'scripts/process_call.py',
        '--file', data['file'],
        '--account', account,
        '--v', version
    ]
    
    result = subprocess.run(
        cmd, 
        cwd='/home/isam/clara-automation',
        capture_output=True, 
        text=True
    )
    
    return jsonify({
        'success': result.returncode == 0,
        'output': result.stdout,
        'error': result.stderr,
        'account_id': account,
        'file': data['file']
    })

@app.route('/batch', methods=['POST'])
def batch():
    """Auto-discover and process all files"""
    calls = discover_files()
    
    # Group by account_id to process demo first, then onboarding
    accounts = {}
    for call in calls:
        acc_id = call['account_id']
        if acc_id not in accounts:
            accounts[acc_id] = {'demo': [], 'onboarding': []}
        accounts[acc_id][call['type']].append(call)
    
    results = []
    
    # Process each account: demo (v1) first, then onboarding (v2)
    for account_id, types in accounts.items():
        # Process demo calls first (v1)
        for call in types['demo']:
            cmd = [
                'uv', 'run', 'python', 
                'scripts/process_call.py',
                '--file', call['file'],
                '--account', account_id,
                '--v', 'v1'
            ]
            
            result = subprocess.run(
                cmd,
                cwd='/home/isam/clara-automation',
                capture_output=True,
                text=True
            )
            
            results.append({
                'file': call['file'],
                'account_id': account_id,
                'version': 'v1',
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            })
        
        # Then process onboarding calls (v2)
        for call in types['onboarding']:
            cmd = [
                'uv', 'run', 'python', 
                'scripts/process_call.py',
                '--file', call['file'],
                '--account', account_id,
                '--v', 'v2'
            ]
            
            result = subprocess.run(
                cmd,
                cwd='/home/isam/clara-automation',
                capture_output=True,
                text=True
            )
            
            results.append({
                'file': call['file'],
                'account_id': account_id,
                'version': 'v2',
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            })
    
    return jsonify({
        'results': results, 
        'total': len(results),
        'successful': sum(1 for r in results if r['success']),
        'accounts_processed': len(accounts)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
