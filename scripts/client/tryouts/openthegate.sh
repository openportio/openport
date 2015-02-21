#curl ...
if [ $# -lt 1 ] ; then
	echo "please input the port"
	exit 1
fi


ip=openport.io
serverport=$2
localport=$1
timeout=5000

ssh -R *:$serverport:localhost:$localport ubuntu@$ip -n -o StrictHostKeyChecking=no -o ExitOnForwardFailure=yes sleep $timeout &
pid=$!

echo "you are now connected, you can connect on $ip:$serverport"

wait $pid

