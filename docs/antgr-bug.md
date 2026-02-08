https://discuss.ai.google.dev/t/can-no-longer-connect-to-devcontainer-after-updating-to-v1-16-5/121479/8

```bash
docker exec -u <user> <container> ln -s \
~/.antigravity-server/bin/1.16.5-<commit> \
~/.antigravity-server/bin/<commit>
```

```bash
for d in ~/.antigravity-server/bin/[0-9]*.[0-9]*.[0-9]*-*; do [ -d "$d" ] && ln -s "$d" "${d%/*}/${d##*-}"; done
```
