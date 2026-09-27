"""AutoDL SSH 助手(paramiko)。用法：python autodl_ssh.py '<远程命令>'  或  -i <本地文件> <远程路径> (上传)"""
import sys, os, paramiko
HOST="connect.bjb2.seetacloud.com"; PORT=53169; USER="root"; PWD=os.environ.get("AUTODL_SSH_PASSWORD", "")
def client():
    c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PWD, timeout=20, banner_timeout=20)
    return c
def run(cmd):
    c=client(); _,out,err=c.exec_command(cmd, timeout=600)
    o=out.read().decode("utf-8","ignore"); e=err.read().decode("utf-8","ignore")
    c.close(); return o,e
def put(local, remote):
    c=client(); sf=c.open_sftp(); sf.put(local, remote); sf.close(); c.close(); print(f"✓ 上传 {local} → {remote}")
if __name__=="__main__":
    if sys.argv[1]=="-i":
        put(sys.argv[2], sys.argv[3])
    else:
        o,e=run(sys.argv[1]); print(o); 
        if e.strip(): print("[stderr]", e[:2000], file=sys.stderr)
