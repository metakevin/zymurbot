REMOTE=192.168.1.183
if [ -z "$REMOTE" ]; then
  echo "Specify remote server as sole argument"
  exit 1
fi

RSYNC="rsync -avt . root@$REMOTE:pi/"

$RSYNC

./onchange.sh $RSYNC


