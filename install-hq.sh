sudo apt update
sudo apt full-upgrade -y
sudo apt install -y python3-picamera2 --no-install-recommends
sudo apt install -y python3-multiprocess
sudo apt install -y python3-protobuf
sudo apt install -y python3-numpy
sudo apt install -y python3-opencv
sudo apt install -y autofs
sudo apt install -y git
sudo apt install -y pmount
sudo apt install -y python3-tk

python -m venv  --system-site-packages .venv
source .venv/bin/activate
echo 'source .venv/bin/activate' >> .profile
echo 'dtoverlay=imx477,cam1' | sudo tee -a /boot/firmware/config.txt
sudo sed '/camera_auto_detect/s/1/0/'  /boot/firmware/config.txt


pip install asyncio
pip install bless
pip install bleak==0.22.3
pip install json_strong_typing
pip install ultralytics
pip install ncnn
pip install picologging
pip install thonny
pip install numpy==1.26.4
pip install lap
pip install gpiozero
pip install pyzmq
pip install aiomultiprocess
pip install pickledb

sudo cp installation-files/yolotrap.service /lib/systemd/system/
sudo systemctl enable yolotrap.service

sudo sed '/bluetoothd/s/bluetoothd/bluetoothd -P battery/'  /etc/systemd/system/dbus-org.bluez.service
mkdir sessions
mkdir configuration
echo "[trap]" >> configuration/config.ini
echo "camera=arducam-hq" >> configuration/config.ini

sudo reboot



