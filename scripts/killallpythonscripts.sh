sudo ps aux|grep bin/python|grep -v grep|awk '{print $2}'|xargs -I {} sudo kill {}
