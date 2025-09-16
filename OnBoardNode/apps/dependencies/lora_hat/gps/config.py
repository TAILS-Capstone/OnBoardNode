#!/usr/bin/python
# -*- coding:utf-8 -*-
import serial
import lgpio

Temp = "0123456789ABCDEF*"


class config(object):
    FORCE = 23
    STANDBY = 6

    def __init__(ser, Baudrate=9600):
        ser.serial = serial.Serial("/dev/ttyAMA0", Baudrate)
        # Open GPIO chip 0
        ser._gpio_handle = lgpio.gpiochip_open(0)
        # Claim FORCE pin as input
        lgpio.gpio_claim_input(ser._gpio_handle, ser.FORCE)
        # Claim STANDBY pin as output with initial value HIGH (1)
        lgpio.gpio_claim_output(ser._gpio_handle, ser.STANDBY, 1)

    def Uart_SendByte(ser, value):
        ser.serial.write(value)

    def Uart_SendString(ser, value):
        ser.serial.write(value)

    def Uart_ReceiveByte(ser):
        return ser.serial.read(1)

    def Uart_ReceiveString(ser, value):
        data = ser.serial.read(value)
        return data

    def Uart_Set_Baudrate(ser, Baudrate):
        ser.serial = serial.Serial("/dev/ttyAMA0", Baudrate)
    
    def get_handler(ser):
        return ser._gpio_handle
