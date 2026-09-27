# Digital Person Fullstack Backup Checklist

Last updated: 2026-07-02

This checklist records what must be backed up for the Digital Person deployment and where the backup should be stored. Keep a copy in both:

- Local repo: `docs/BACKUP_CHECKLIST.md`
- AutoDL cloud disk: `/root/autodl-tmp/backups/BACKUP_CHECKLIST.md`

## Backup Destination

Use a timestamped directory on the AutoDL cloud disk:

```bash
/root/autodl-tmp/backups/digital_person_fullstack_YYYYMMDD_HHMMSS
```

Maintain a convenience symlink:

```bash
/root/autodl-tmp/backups/digital_person_fullstack_latest
```

## AutoDL Items

Archive name:

```bash
autodl_core_YYYYMMDD_HHMMSS.tgz
```

Include:

- `/root/autodl-tmp/Digital_Person`
- `/root/autodl-tmp/LiveTalking`
- `/root/digital-human`
- `/root/autodl-tmp/supervisord.conf`
- `/root/autodl-tmp/dp_up.sh`
- `/root/autodl-tmp/dp_down.sh`
- `/root/autodl-tmp/relay_hz.sh`
- `/root/autodl-tmp/lt_run.sh`
- `/root/autodl-tmp/lt_run_portrait.sh`
- `/root/autodl-tmp/srs/trunk/conf/srs_dp.conf`

Exclude:

- `node_modules`
- `.venv` under `Digital_Person`
- `__pycache__`
- transient browser/build caches

## ECS Items

Archive name:

```bash
ecs_gateway_YYYYMMDD_HHMMSS.tgz
```

Include current serving assets:

- `/var/www/webapp`
- `/var/www/admin`
- `/var/www/kiosk`

Include gateway/runtime config:

- `/etc/nginx/nginx.conf`
- `/etc/nginx/sites-available/default`
- `/etc/nginx/sites-enabled/default`
- `/root/srs.conf`
- `/root/srs.conf.bak*`

Optional if present:

- `/root/admin_deploy_tmp`

Do not include old `/var/www/*.bak*` directories unless the explicit goal is forensic history; they are deployment backups and can make archives noisy.

## Runtime Snapshots

Save these text snapshots into the same backup directory:

- `autodl_runtime_snapshot.txt`
  - `date`
  - `df -h /root /root/autodl-tmp`
  - `supervisorctl -c /root/autodl-tmp/supervisord.conf status`
  - `ps` for `uvicorn`, `livetalking`, `srs`, `relay_hz`
  - `du -sh` for backed up paths

- `ecs_runtime_snapshot.txt`
  - `date`
  - `df -h / /var /root`
  - `ss -lunpt` for `8443`, `8000`, `1935`, `1985`, `8080`
  - `docker ps`
  - `du -sh` for backed up paths

## Verification

After creating archives, generate:

```bash
sha256sums.txt
manifest.txt
```

Minimum checks:

```bash
tar -tzf autodl_core_YYYYMMDD_HHMMSS.tgz >/dev/null
tar -tzf ecs_gateway_YYYYMMDD_HHMMSS.tgz >/dev/null
sha256sum -c sha256sums.txt
```

Confirm the backup directory size:

```bash
du -sh /root/autodl-tmp/backups/digital_person_fullstack_YYYYMMDD_HHMMSS
```

## Restore Notes

AutoDL:

- Restore `Digital_Person` to `/root/autodl-tmp/Digital_Person`.
- Restore `LiveTalking` to `/root/autodl-tmp/LiveTalking`.
- Restore `digital-human` to `/root/digital-human`.
- Restore supervisor and run scripts to `/root/autodl-tmp`.
- Restart with `/root/autodl-tmp/dp_up.sh` or supervisor commands.

ECS:

- Restore web roots to `/var/www/webapp`, `/var/www/admin`, `/var/www/kiosk`.
- Restore nginx config, then run `nginx -t` before reload.
- Restore `/root/srs.conf`, then restart the SRS container if needed.

## Current Production Endpoints To Verify After Restore

- Visitor web: `https://114.55.178.51:8443/`
- Admin web: `https://114.55.178.51:8443/admin/`
- WebRTC API: `https://114.55.178.51:8443/rtc/v1/play/`
- HLS fallback: `https://114.55.178.51:8443/hls/livestream.m3u8`
- Bridge health: `https://114.55.178.51:8443/live/capacity`
