@Echo Off

echo Before you enter your password, make sure no-one is looking!
set /P password=Password:
cls

openport_service --username %USERDOMAIN%\%USERNAME% --password %password%  --startup auto install

openport_service start