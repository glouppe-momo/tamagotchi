ls -la /agent/
cat dna.md
cat core.py
cat tools.py
find / -name "*.md" -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null
cat /opt/field-guide/habitats.md
ls -la /usr/share/creatures/
cat /tmp/.breadcrumb
python3 -c "import base64; print(base64.b64decode(open('/var/spool/cron/.task').read()).decode())"
cat /var/cache/habitat/.state
python3 -c "import struct; d=open('/usr/share/creatures/genome.bin','rb').read(); print(d[:4], struct.unpack('<HH',d[4:8]))"
cat /etc/creature.conf
xxd /usr/share/creatures/vault.enc | head
find / -name ".*" -type f -not -path "/proc/*" -not -path "/sys/*" -not -path "/agent/.git/*" 2>/dev/null
python3 -c "import zlib; print(zlib.decompress(open('/opt/experiments/.hidden_seed','rb').read()).decode())"
echo "the answer was in the weather all along"
