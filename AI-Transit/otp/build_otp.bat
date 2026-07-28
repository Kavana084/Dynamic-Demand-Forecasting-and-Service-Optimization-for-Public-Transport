@echo off
echo Building OpenTripPlanner Graph...
java -Xmx8G -jar otp.jar --build --save ./
echo Build complete.
