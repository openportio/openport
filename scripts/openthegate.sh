#curl ...
if [ $# -lt 1 ] ; then
	echo "please input the port"
	exit 1
fi


ip=46.137.72.214
serverport=2022
localport=$1
timeout=5000

ssh -R *:$serverport:localhost:$localport open@$ip -n -o StrictHostKeyChecking=no -o ExitOnForwardFailure=yes sleep $timeout &
pid=$!

echo "you are now connected, you can connect on $ip:$serverport"

wait $pid

