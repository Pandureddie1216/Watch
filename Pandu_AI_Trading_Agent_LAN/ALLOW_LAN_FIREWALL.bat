@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Right-click this file and choose "Run as administrator".
  pause
  exit /b 1
)
netsh advfirewall firewall delete rule name="Pandu AI Trading Agent LAN 8502" >nul 2>&1
netsh advfirewall firewall add rule name="Pandu AI Trading Agent LAN 8502" dir=in action=allow protocol=TCP localport=8502 profile=private
if %errorlevel% equ 0 (
  echo Firewall rule added for TCP port 8502 on Private networks.
) else (
  echo Failed to add firewall rule.
)
pause
