#!/usr/bin/env python3
import argparse
import json
import os
import smtplib
import subprocess
import sys
import time
from email.message import EmailMessage
from typing import List, Dict, Optional


def _run_nvidia_smi() -> str:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    return subprocess.check_output(cmd, text=True)


def _parse_nvidia_smi(output: str) -> List[Dict[str, int]]:
    gpus = []
    for line in output.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            continue
        idx, util, mem_used, mem_total = map(int, parts)
        gpus.append(
            {
                "index": idx,
                "util": util,
                "mem_used": mem_used,
                "mem_total": mem_total,
            }
        )
    return gpus


def _is_gpu_idle(gpu: Dict[str, int], util_th: int, mem_th: int) -> bool:
    return gpu["util"] <= util_th and gpu["mem_used"] <= mem_th


def _send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: Optional[str],
    smtp_pass: Optional[str],
    sender: str,
    recipients: List[str],
    subject: str,
    body: str,
    use_ssl: bool,
    use_tls: bool,
) -> None:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as s:
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            if use_tls:
                s.starttls()
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)


def main() -> int:
    ap = argparse.ArgumentParser(description="Monitor GPU and alert when any GPU is idle.")
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between checks")
    ap.add_argument("--util_th", type=int, default=5, help="utilization threshold (<= considered idle)")
    ap.add_argument("--mem_th", type=int, default=500, help="memory used threshold in MB (<= considered idle)")
    ap.add_argument("--once", action="store_true", help="check once and exit")
    ap.add_argument("--json", action="store_true", help="print status as JSON")

    ap.add_argument("--email", action="store_true", help="enable email notification")
    ap.add_argument("--email_to", type=str, default="", help="comma-separated recipients")
    ap.add_argument("--smtp_host", type=str, default="", help="SMTP host (or env SMTP_HOST)")
    ap.add_argument("--smtp_port", type=int, default=0, help="SMTP port (or env SMTP_PORT)")
    ap.add_argument("--smtp_user", type=str, default="", help="SMTP user (or env SMTP_USER)")
    ap.add_argument("--smtp_pass", type=str, default="", help="SMTP pass/app password (or env SMTP_PASS)")
    ap.add_argument("--smtp_sender", type=str, default="", help="Sender email (or env SMTP_SENDER)")
    ap.add_argument("--smtp_ssl", action="store_true", help="use SMTP SSL")
    ap.add_argument("--smtp_tls", action="store_true", help="use STARTTLS")
    args = ap.parse_args()

    while True:
        try:
            out = _run_nvidia_smi()
        except Exception as e:
            print(f"ERROR: failed to run nvidia-smi: {e}", file=sys.stderr)
            return 2

        gpus = _parse_nvidia_smi(out)
        idle = [g for g in gpus if _is_gpu_idle(g, args.util_th, args.mem_th)]

        if args.json:
            print(json.dumps({"gpus": gpus, "idle": idle}, ensure_ascii=False))
        else:
            for g in gpus:
                print(
                    f"GPU {g['index']}: util={g['util']}% mem={g['mem_used']}/{g['mem_total']} MB"
                )

        if idle:
            idle_ids = ",".join(str(g["index"]) for g in idle)
            print(f"ALERT: idle GPU(s) detected -> {idle_ids}")
            try:
                sys.stdout.write("\a")
                sys.stdout.flush()
            except Exception:
                pass
            if args.email:
                smtp_host = args.smtp_host or os.getenv("SMTP_HOST", "")
                smtp_port = args.smtp_port or int(os.getenv("SMTP_PORT", "0") or 0)
                smtp_user = args.smtp_user or os.getenv("SMTP_USER", "")
                smtp_pass = args.smtp_pass or os.getenv("SMTP_PASS", "")
                smtp_sender = args.smtp_sender or os.getenv("SMTP_SENDER", smtp_user)
                recipients = [r.strip() for r in (args.email_to or os.getenv("SMTP_TO", "")).split(",") if r.strip()]

                if smtp_host and smtp_port and smtp_sender and recipients:
                    subject = f"GPU idle alert: {idle_ids}"
                    body = "\n".join(
                        [f"GPU {g['index']}: util={g['util']}% mem={g['mem_used']}/{g['mem_total']} MB" for g in gpus]
                    )
                    try:
                        _send_email(
                            smtp_host=smtp_host,
                            smtp_port=int(smtp_port),
                            smtp_user=smtp_user or None,
                            smtp_pass=smtp_pass or None,
                            sender=smtp_sender,
                            recipients=recipients,
                            subject=subject,
                            body=body,
                            use_ssl=bool(args.smtp_ssl),
                            use_tls=bool(args.smtp_tls),
                        )
                        print("Email alert sent.")
                    except Exception as e:
                        print(f"Email alert failed: {e}")
                else:
                    print("Email alert skipped: missing SMTP config.")
            if args.once:
                return 0
        else:
            if args.once:
                return 1

        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
