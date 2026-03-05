import os
import json
import argparse
import re
from pathlib import Path
from dotenv import load_dotenv
from faster_whisper import WhisperModel
import ollama
import requests

load_dotenv()

def get_transcript(file_path):
    """Detects file type and returns text content. Handles .txt and Media."""
    ext = Path(file_path).suffix.lower()
    
    if ext in [".txt", ".md"]:
        print(f"Loading text transcript: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
            
    elif ext in [".m4a", ".mp4", ".mp3", ".wav"]:
        print(f"Transcribing media: {file_path}")
        model = WhisperModel(
            os.getenv("WHISPER_MODEL", "small"), 
            device="cuda", 
            compute_type="float16"
        )
        segments, _ = model.transcribe(file_path)
        return " ".join([s.text for s in segments])
    return None

def extract_account_data(transcript, account_id):
    """
    Ollama extraction logic. 
    Enforces strict 'No Hallucination' and 'Missing Data' principles.
    """
    # define the specific data points required for your principles
    prompt = f"""
    Extract information from the transcript below and return ONLY a valid JSON object with no additional text.

    Rules:
    - Use null for missing information
    - Do not add explanatory text before or after the JSON
    - Do not use markdown code fences
    - Do not add fields not in the schema

    Transcript:
    {transcript}

    Return this exact structure:
    {{
      "account_id": "{account_id}",
      "company_name": null,
      "business_hours": {{
        "days": null,
        "start": null,
        "end": null,
        "timezone": null
      }},
      "office_address": null,
      "services_supported": [],
      "emergency_definition": [],
      "emergency_routing_rules": {{
        "who_to_call": null,
        "order": null,
        "fallback": null
      }},
      "non_emergency_routing_rules": null,
      "call_transfer_rules": {{
        "timeouts": null,
        "retries": null,
        "error_message": null
      }},
      "integration_constraints": [],
      "after_hours_flow_summary": null,
      "office_hours_flow_summary": null,
      "questions_or_unknowns": [],
    }}

    Replace null values with extracted data. Keep null if not found in transcript.
    RESPOND ONLY WITH A VALID JSON OBJECT. DO NOT INCLUDE ANY OTHER TEXT OR EXPLANATIONS.
    """

    response = ollama.generate(model=os.getenv("OLLAMA_MODEL", "llama3"), prompt=prompt)
    raw_text = response['response'].strip()
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match: 
        return json.loads(match.group())
    raise ValueError("LLM failed to return valid JSON.")

def patch_v2_data(v1_data, v2_new):
    """Merges v2 extraction into v1. Keeps v1 values unless v2 provides a non-null update."""
    def merge_recursive(base, patch):
        for key, value in patch.items():
            if value is not None and value != [] and value != {}:
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    merge_recursive(base[key], value)
                else:
                    base[key] = value
        return base
    
    merged = merge_recursive(json.loads(json.dumps(v1_data)), v2_new)
    # refresh unknowns list based on merged state
    unknowns = []
    for k, v in merged.items():
        if v is None or v == [] or v == "": unknowns.append(k)
        elif isinstance(v, dict):
            for sk, sv in v.items():
                if sv is None: unknowns.append(f"{k}.{sk}")
    merged["questions_or_unknowns"] = unknowns
    return merged

def create_change_log(v1, v2, prefix=""):
    """
    Recursively compares v1 and v2 to find fields that transitioned 
    from NULL/Empty to having a value.
    """
    logs = []
    
    for key, value in v2.items():
        # Construct the full path (e.g., business_hours.start)
        full_key = f"{prefix}.{key}" if prefix else key
        if key == "questions_or_unknowns":
            continue
        
        # If it's a nested dictionary, recurse into it
        if isinstance(value, dict) and key in v1 and isinstance(v1[key], dict):
            logs.extend(create_change_log(v1[key], value, full_key))
        
        # If the field was NULL or empty in v1 but has a value in v2
        elif key in v1:
            v1_val = v1[key]
            # Check if it was effectively empty in v1 but is now populated
            was_empty = v1_val is None or v1_val == [] or v1_val == ""
            is_now_filled = value is not None and value != [] and value != ""
            
            if was_empty and is_now_filled:
                logs.append(f"UPDATED: {full_key} (was NULL, now populated)")
    return logs

def create_github_issue(account_id, status):
    """Create Github issue as task tracker"""
    token = os.getenv("GITHUB_TOKEN")
    repo = "iamisam/clara-automation"
    requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={"Authorization": f"token {token}"},
            json={
            "title": f"Onboarding: {account_id}",
            "body": f"Status: {status}\nAccount: {account_id}",
            "labels": ["onboarding"]
        })

def generate_agent_spec(data, version):
    """Generic template for Agent Spec Schema used by both v1 and v2."""
    biz_name = data.get('company_name') or 'Valued Client'
    hours = data.get('business_hours') or {}
    
    system_prompt = f"""
    ROLE: Clara, AI Receptionist for {biz_name}.
    OFFICE HOURS: {hours.get('start', 'NULL')} - {hours.get('end', 'NULL')} ({hours.get('timezone', 'NULL')}).
    
    BUSINESS HOURS FLOW:
    - Greet, ask for Name, Number, and Purpose.
    - {data.get('office_hours_flow_summary') or 'Transfer to main office.'}
    
    AFTER-HOURS FLOW:
    - Greet and check for emergency: {", ".join(data.get('emergency_definition', [])) or 'Standard emergency protocol.'}.
    - {data.get('after_hours_flow_summary') or 'Inform caller of follow-up next business day.'}
    """
    
    return {
        "agent_name": "Clara",
        "voice_style": "Professional (Formal)",
        "system_prompt": system_prompt.strip(),
        "key_variables": {
            "timezone": hours.get("timezone"),
            "business_hours": f"{hours.get('start')} - {hours.get('end')}",
            "address": data.get("office_address"),
            "emergency_routing": data.get("emergency_routing_rules", {}).get("who_to_call")
        },
        "tool_invocation_placeholders": ["{{calendar_sync}}", "{{transfer_call}}"],
        "call_transfer_protocol": data.get("call_transfer_rules"),
        "version": version
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--v", choices=['v1', 'v2'], default='v1')
    args = parser.parse_args()

    # Acquire text content
    text_content = get_transcript(args.file)
    if not text_content:
        print(f"Error: Unsupported file format for {args.file}")
        return

    # Process with LLM
    extracted = extract_account_data(text_content, args.account)
    
    # Save to structured directory
    account_dir = Path(os.getenv("OUTPUT_PATH", "./outputs/accounts")) / args.account
    v1_path = account_dir / "v1" / "v1.json"
    
    # Logic for v2 Patching
    final_json = extracted
    if args.v == "v2" and v1_path.exists():
        with open(v1_path, "r") as f:
            v1_data = json.load(f)
        final_json = patch_v2_data(v1_data, extracted)
        changelog = create_change_log(v1_data, final_json)
        
        log_path = account_dir / "changelog.txt"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            f.write("\n".join(changelog))

    # Generate Agent Spec
    spec = generate_agent_spec(final_json, args.v)

    # Save
    out_dir = account_dir / args.v
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{args.v}.json", "w") as f:
        json.dump(final_json, f, indent=2)
    with open(out_dir / "agent_spec.json", "w") as f:
        json.dump(spec, f, indent=2)

    print(f"Processed {args.v} for {args.account}")

if __name__ == "__main__":
    main()
