# export LD_LIBRARY_PATH=~/mylib:$D_LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/local/lib64
export SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt
ps -ef | grep myflask.py | awk '{print $2}' | xargs kill $1
nohup python3.9 myflask.py & 
tail -f ./chat.log