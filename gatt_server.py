from __future__ import print_function
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

import array

import functools

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

from random import randint

import exceptions
import adapters

BLUEZ_SERVICE_NAME = "org.bluez"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"

LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"

GATT_MANAGER_IFACE = "org.bluez.GattManager1"

GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
GATT_DESC_IFACE = "org.bluez.GattDescriptor1"


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """

    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(HIDService(bus, 0))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        print("GetManagedObjects")

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """

    PATH_BASE = "/org/bluez/example/service"

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(
                    self.get_characteristic_paths(), signature="o"
                ),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
                "Descriptors": dbus.Array(self.get_descriptor_paths(), signature="o"),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        print("Default ReadValue called, returning error")
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        print("Default WriteValue called, returning error")
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print("Default StartNotify called, returning error")
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print("Default StopNotify called, returning error")
        raise exceptions.NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + "/desc" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_DESC_IFACE: {
                "Characteristic": self.chrc.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        print("Default ReadValue called, returning error")
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        print("Default WriteValue called, returning error")
        raise exceptions.NotSupportedException()


class HeartRateService(Service):
    """
    Fake Heart Rate Service that simulates a fake heart beat and control point
    behavior.

    """

    HR_UUID = "0000180d-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.HR_UUID, True)
        self.add_characteristic(HeartRateMeasurementChrc(bus, 0, self))
        self.add_characteristic(BodySensorLocationChrc(bus, 1, self))
        self.add_characteristic(HeartRateControlPointChrc(bus, 2, self))
        self.energy_expended = 0


class HeartRateMeasurementChrc(Characteristic):
    HR_MSRMT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.HR_MSRMT_UUID, ["notify"], service
        )
        self.notifying = False
        self.hr_ee_count = 0

    def hr_msrmt_cb(self):
        value = []
        value.append(dbus.Byte(0x06))

        value.append(dbus.Byte(randint(90, 130)))

        if self.hr_ee_count % 10 == 0:
            value[0] = dbus.Byte(value[0] | 0x08)
            value.append(dbus.Byte(self.service.energy_expended & 0xFF))
            value.append(dbus.Byte((self.service.energy_expended >> 8) & 0xFF))

        self.service.energy_expended = min(0xFFFF, self.service.energy_expended + 1)
        self.hr_ee_count += 1

        print("Updating value: " + repr(value))

        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])

        return self.notifying

    def _update_hr_msrmt_simulation(self):
        print("Update HR Measurement Simulation")

        if not self.notifying:
            return

        GObject.timeout_add(1000, self.hr_msrmt_cb)

    def StartNotify(self):
        if self.notifying:
            print("Already notifying, nothing to do")
            return

        self.notifying = True
        self._update_hr_msrmt_simulation()

    def StopNotify(self):
        if not self.notifying:
            print("Not notifying, nothing to do")
            return

        self.notifying = False
        self._update_hr_msrmt_simulation()


class BodySensorLocationChrc(Characteristic):
    BODY_SNSR_LOC_UUID = "00002a38-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.BODY_SNSR_LOC_UUID, ["read"], service
        )

    def ReadValue(self, options):
        # Return 'Chest' as the sensor location.
        return [0x01]


class HeartRateControlPointChrc(Characteristic):
    HR_CTRL_PT_UUID = "00002a39-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.HR_CTRL_PT_UUID, ["write"], service
        )

    def WriteValue(self, value, options):
        print("Heart Rate Control Point WriteValue called")

        if len(value) != 1:
            raise exceptions.InvalidValueLengthException()

        byte = value[0]
        print("Control Point value: " + repr(byte))

        if byte != 1:
            raise exceptions.FailedException("0x80")

        print("Energy Expended field reset!")
        self.service.energy_expended = 0


class BatteryService(Service):
    """
    Fake Battery service that emulates a draining battery.

    """

    BATTERY_UUID = "180f"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.BATTERY_UUID, True)
        self.add_characteristic(BatteryLevelCharacteristic(bus, 0, self))


class BatteryLevelCharacteristic(Characteristic):
    """
    Fake Battery Level characteristic. The battery level is drained by 2 points
    every 5 seconds.

    """

    BATTERY_LVL_UUID = "2a19"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.BATTERY_LVL_UUID, ["read", "notify"], service
        )
        self.notifying = False
        self.battery_lvl = 100
        GObject.timeout_add(5000, self.drain_battery)

    def notify_battery_level(self):
        if not self.notifying:
            return
        self.PropertiesChanged(
            GATT_CHRC_IFACE, {"Value": [dbus.Byte(self.battery_lvl)]}, []
        )

    def drain_battery(self):
        if self.battery_lvl > 0:
            self.battery_lvl -= 2
            if self.battery_lvl < 0:
                self.battery_lvl = 0
        print("Battery level: " + repr(self.battery_lvl))
        self.notify_battery_level()
        return True

    def ReadValue(self, options):
        print("Battery level read: " + repr(self.battery_lvl))
        return [dbus.Byte(self.battery_lvl)]

    def StartNotify(self):
        if self.notifying:
            print("Already notifying, nothing to do")
            return

        self.notifying = True
        self.notify_battery_level()

    def StopNotify(self):
        if not self.notifying:
            print("Not notifying, nothing to do")
            return

        self.notifying = False


class TestService(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.

    """

    TEST_SVC_UUID = "12345678-1234-5678-1234-56789abcdef0"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SVC_UUID, True)
        self.add_characteristic(TestCharacteristic(bus, 0, self))
        self.add_characteristic(TestEncryptCharacteristic(bus, 1, self))
        self.add_characteristic(TestSecureCharacteristic(bus, 2, self))


class TestCharacteristic(Characteristic):
    """
    Dummy test characteristic. Allows writing arbitrary bytes to its value, and
    contains "extended properties", as well as a test descriptor.

    """

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef1"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.TEST_CHRC_UUID,
            ["read", "write", "writable-auxiliaries"],
            service,
        )
        self.value = []
        self.add_descriptor(TestDescriptor(bus, 0, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print("TestCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("TestCharacteristic Write: " + repr(value))
        self.value = value


class TestDescriptor(Descriptor):
    """
    Dummy test descriptor. Returns a static value.

    """

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef2"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self, bus, index, self.TEST_DESC_UUID, ["read", "write"], characteristic
        )

    def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.

    """

    CUD_UUID = "2901"

    def __init__(self, bus, index, characteristic):
        self.writable = "writable-auxiliaries" in characteristic.flags
        self.value = array.array("B", b"This is a characteristic for testing")
        self.value = self.value.tolist()
        Descriptor.__init__(
            self, bus, index, self.CUD_UUID, ["read", "write"], characteristic
        )

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise exceptions.NotPermittedException()
        self.value = value


class TestEncryptCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring encryption.

    """

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef3"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.TEST_CHRC_UUID,
            ["encrypt-read", "encrypt-write"],
            service,
        )
        self.value = []
        self.add_descriptor(TestEncryptDescriptor(bus, 2, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, options):
        print("TestEncryptCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("TestEncryptCharacteristic Write: " + repr(value))
        self.value = value


class TestEncryptDescriptor(Descriptor):
    """
    Dummy test descriptor requiring encryption. Returns a static value.

    """

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef4"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self,
            bus,
            index,
            self.TEST_DESC_UUID,
            ["encrypt-read", "encrypt-write"],
            characteristic,
        )

    def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


class TestSecureCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring secure connection.

    """

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef5"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.TEST_CHRC_UUID,
            ["secure-read", "secure-write"],
            service,
        )
        self.value = []
        self.add_descriptor(TestSecureDescriptor(bus, 2, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, options):
        print("TestSecureCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print("TestSecureCharacteristic Write: " + repr(value))
        self.value = value


class TestSecureDescriptor(Descriptor):
    """
    Dummy test descriptor requiring secure connection. Returns a static value.

    """

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef6"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self,
            bus,
            index,
            self.TEST_DESC_UUID,
            ["secure-read", "secure-write"],
            characteristic,
        )

    def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


def register_app_cb():
    print("GATT application registered")


def register_app_error_cb(mainloop, error):
    print("Failed to register application: " + str(error))
    mainloop.quit()


def gatt_server_main(mainloop, bus, adapter_name):
    adapter = adapters.find_adapter(bus, GATT_MANAGER_IFACE, adapter_name)
    if not adapter:
        raise Exception("GattManager1 interface not found")

    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter), GATT_MANAGER_IFACE
    )

    app = Application(bus)

    print("Registering GATT application...")

    service_manager.RegisterApplication(
        app.get_path(),
        {},
        reply_handler=register_app_cb,
        error_handler=functools.partial(register_app_error_cb, mainloop),
    )


# name="Human Interface Device" sourceId="org.bluetooth.service.human_interface_device" type="primary" uuid="1812"
class HIDService(Service):
    SERVICE_UUID = "1812"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.SERVICE_UUID, True)

        self.protocolMode = ProtocolModeCharacteristic(bus, 0, self)
        self.hidInfo = HIDInfoCharacteristic(bus, 1, self)
        self.controlPoint = ControlPointCharacteristic(bus, 2, self)
        self.reportMap = ReportMapCharacteristic(bus, 3, self)
        self.report1 = Report1Characteristic(bus, 4, self)
        self.report2 = Report2Characteristic(bus, 5, self)

        self.add_characteristic(self.protocolMode)
        self.add_characteristic(self.hidInfo)
        self.add_characteristic(self.controlPoint)
        self.add_characteristic(self.reportMap)
        self.add_characteristic(self.report1)
        self.add_characteristic(self.report2)


# name="Protocol Mode" sourceId="org.bluetooth.characteristic.protocol_mode" uuid="2A4E"
class ProtocolModeCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = "2A4E"

    def __init__(self, bus, index, service):

        Characteristic.__init__(
            self,
            bus,
            index,
            self.CHARACTERISTIC_UUID,
            ["read", "write-without-response"],
            service,
        )

        """        
        <Field name="Protocol Mode Value">
        <Requirement>Mandatory</Requirement>
        <Format>uint8</Format>
        <Enumerations>
        <Enumeration key="0" value="Boot Protocol Mode"/>
        <Enumeration key="1" value="Report Protocol Mode"/>
        <ReservedForFutureUse start="2" end="255"/>
        </Enumerations>
        """

        # self.value = dbus.Array([1], signature=dbus.Signature('y'))
        self.parent = service
        self.value = dbus.Array(bytearray.fromhex("01"), signature=dbus.Signature("y"))
        print(f"***ProtocolMode value***: {self.value}")

    def ReadValue(self, options):
        print(f"Read ProtocolMode: {self.value}")
        return self.value

    def WriteValue(self, value, options):
        print(f"Write ProtocolMode {value}")
        self.value = value


# id="hid_information" name="HID Information" sourceId="org.bluetooth.characteristic.hid_information" uuid="2A4A"
class HIDInfoCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = "2A4A"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.CHARACTERISTIC_UUID, ["read"], service
        )

        """
        <Field name="bcdHID">
            <InformativeText>16-bit unsigned integer representing version number of base USB HID Specification implemented by HID Device</InformativeText>
            <Requirement>Mandatory</Requirement>
            <Format>uint16</Format>
        </Field>
        
        <Field name="bCountryCode">
            <InformativeText>Identifies which country the hardware is localized for. Most hardware is not localized and thus this value would be zero (0).</InformativeText>
            <Requirement>Mandatory</Requirement>
            <Format>8bit</Format>
        </Field>
        
        <Field name="Flags">
            <Requirement>Mandatory</Requirement>
            <Format>8bit</Format>
            <BitField>
                <Bit index="0" size="1" name="RemoteWake">
                <Enumerations>
                    <Enumeration key="0" value="The device is not designed to be capable of providing wake-up signal to a HID host"/>
                    <Enumeration key="1" value="The device is designed to be capable of providing wake-up signal to a HID host"/>
                </Enumerations>
                </Bit>
            
                <Bit index="1" size="1" name="NormallyConnectable">
                <Enumerations>
                    <Enumeration key="0" value="The device is not normally connectable"/>
                    <Enumeration key="1" value="The device is normally connectable"/>
                </Enumerations>
                </Bit>
            
                <ReservedForFutureUse index="2" size="6"/>
            </BitField>
        </Field>
        """

        self.value = dbus.Array(
            bytearray.fromhex("01110002"), signature=dbus.Signature("y")
        )
        print(f"***HIDInformation value***: {self.value}")

    def ReadValue(self, options):
        print(f"Read HIDInformation: {self.value}")
        return self.value


# sourceId="org.bluetooth.characteristic.hid_control_point" uuid="2A4C"
class ControlPointCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = "2A4C"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.CHARACTERISTIC_UUID,
            ["write-without-response"],
            service,
        )

        self.value = dbus.Array(bytearray.fromhex("00"), signature=dbus.Signature("y"))
        print(f"***ControlPoint value***: {self.value}")

    def WriteValue(self, value, options):
        print(f"Write ControlPoint {value}")
        self.value = value


# sourceId="org.bluetooth.characteristic.report_map" uuid="2A4B"
class ReportMapCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = "2A4B"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.CHARACTERISTIC_UUID, ["read"], service
        )
        """
        <Field name="Report Map Value">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Repeated>true</Repeated>
        </Field>
        
        HID Report Descriptors https://www.usb.org/sites/default/files/documents/hid1_11.pdf
        HID Report Parser https://eleccelerator.com/usbdescreqparser/
        """

        ##############################################################################################
        # This Report Descriptor defines 2 Input Reports
        # ReportMap designed by HeadHodge
        #
        # <Report Layouts>
        #   <Report>
        #       <ReportId>1</ReportId>
        #       <Description>HID Keyboard Input</Description>
        #       <Example>KeyCode capital 'M' = [dbus.Byte(0x02), dbus.Byte(0x10)]</Example>
        #       <Field>
        #           <Name>Keyboard Modifier</Name>
        #           <Size>uint8</Size>
        #           <Format>
        #               <Bit0>Left CTRL Key Pressed</Bit0>
        #               <Bit1>Left SHIFT Key Pressed</Bit1>
        #               <Bit2>Left ALT Key Pressed</Bit2>
        #               <Bit3>Left CMD(Window) Key Pressed</Bit3>
        #               <Bit4>Right CTRL Key Pressed</Bit4>
        #               <Bit5>Right SHIFT Key Pressed</Bit5>
        #               <Bit6>Right ALT Key Pressed</Bit6>
        #               <Bit7>Right CMD(Window) Key Pressed</Bit7>
        #           </Format>
        #       </Field>
        #       <Field>
        #           <Name>Keyboard Input KeyCode</Name>
        #           <Size>uint8</Size>
        #       </Field>
        #   </Report>
        #   <Report>
        #       <ReportId>2</ReportId>
        #       <Description>HID Consumer Input</Description>
        #       <Example>KeyCode 'VolumeUp' = [dbus.Byte(0xe9), dbus.Byte(0x00)]</Example>
        #       <Field>
        #           <Name>Consumer Input KeyCode</Name>
        #           <Size>uint16</Size>
        #       </Field>
        #   </Report>
        # </Report Layouts>
        ##############################################################################################

        # USB HID Report Descriptor
        self.value = dbus.Array(
            bytearray.fromhex(
                "05010906a1018501050719e029e71500250175019508810295017508150025650507190029658100c0050C0901A101850275109501150126ff0719012Aff078100C0"
            )
        )
        print(f"***ReportMap value***: {self.value}")

    def ReadValue(self, options):
        print(f"Read ReportMap: {self.value}")
        return self.value


# id="report" name="Report" sourceId="org.bluetooth.characteristic.report" uuid="2A4D"
class Report1Characteristic(Characteristic):

    CHARACTERISTIC_UUID = "2A4D"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.CHARACTERISTIC_UUID,
            ["secure-read", "notify"],
            service,
        )

        """
        <Field name="Report Value">
        <Requirement>Mandatory</Requirement>
        <Format>uint8</Format>
        <Repeated>true</Repeated>
        </Field>
        
        Use standard key codes: https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf
        """

        self.add_descriptor(Report1ReferenceDescriptor(bus, 1, self))

        self.value = [dbus.Byte(0x00), dbus.Byte(0x00)]
        print(f"***Report value***: {self.value}")

    def send(self):

        # send keyCode: 'M'
        print(f'***send keyCode: "M"***')
        self.PropertiesChanged(
            GATT_CHRC_IFACE, {"Value": [dbus.Byte(0x02), dbus.Byte(0x10)]}, []
        )
        self.PropertiesChanged(
            GATT_CHRC_IFACE, {"Value": [dbus.Byte(0x00), dbus.Byte(0x00)]}, []
        )
        print(f"***sent***")
        return True

    def ReadValue(self, options):
        print(f"Read Report: {self.value}")
        return self.value

    def WriteValue(self, value, options):
        print(f"Write Report {self.value}")
        self.value = value

    def StartNotify(self):
        print(f"Start Start Report Keyboard Input")
        GObject.timeout_add(10000, self.send)

    def StopNotify(self):
        print(f"Stop Report Keyboard Input")


# type="org.bluetooth.descriptor.report_reference" uuid="2908"
class Report1ReferenceDescriptor(Descriptor):

    DESCRIPTOR_UUID = "2908"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self, bus, index, self.DESCRIPTOR_UUID, ["read"], characteristic
        )

        """
        <Field name="Report ID">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>0</Minimum>
            <Maximum>255</Maximum>
        </Field>
        
        <Field name="Report Type">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>1</Minimum>
            <Maximum>3</Maximum>
            <Enumerations>
                <Enumeration value="Input Report" key="1"/>
                <Enumeration value="Output report" key="2"/>
                <Enumeration value="Feature Report" key="3"/>
                <ReservedForFutureUse start="4" end="255"/>
                <ReservedForFutureUse1 start1="0" end1="0"/>
            </Enumerations>
        </Field>
        """

        # This report uses ReportId 1 as defined in the ReportMap characteristic
        self.value = dbus.Array(
            bytearray.fromhex("0101"), signature=dbus.Signature("y")
        )
        print(f"***ReportReference***: {self.value}")

    def ReadValue(self, options):
        print(f"Read ReportReference: {self.value}")
        return self.value


# id="report" name="Report" sourceId="org.bluetooth.characteristic.report" uuid="2A4D"
class Report2Characteristic(Characteristic):

    CHARACTERISTIC_UUID = "2A4D"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            self.CHARACTERISTIC_UUID,
            ["secure-read", "notify"],
            service,
        )

        """
        <Field name="Report Value">
        <Requirement>Mandatory</Requirement>
        <Format>uint8</Format>
        <Repeated>true</Repeated>
        </Field>
        
        Use standard key codes: https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf
        """

        self.add_descriptor(Report2ReferenceDescriptor(bus, 1, self))

        self.value = [dbus.Byte(0x00), dbus.Byte(0x00)]
        print(f"***Report value***: {self.value}")

    def send(self):

        # send keyCode: 'VolumeUp'
        print(f'***send keyCode: "VolumeUp"***')
        self.PropertiesChanged(
            GATT_CHRC_IFACE, {"Value": [dbus.Byte(0xE9), dbus.Byte(0x00)]}, []
        )
        self.PropertiesChanged(
            GATT_CHRC_IFACE, {"Value": [dbus.Byte(0x00), dbus.Byte(0x00)]}, []
        )
        print(f"***sent***")
        return True

    def ReadValue(self, options):
        print(f"Read Report: {self.value}")
        return self.value

    def WriteValue(self, value, options):
        print(f"Write Report {self.value}")
        self.value = value

    def StartNotify(self):
        print(f"Start Report Consumer Input")
        GObject.timeout_add(15000, self.send)

    def StopNotify(self):
        print(f"Stop Start Report Consumer Input")


# type="org.bluetooth.descriptor.report_reference" uuid="2908"
class Report2ReferenceDescriptor(Descriptor):

    DESCRIPTOR_UUID = "2908"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
            self, bus, index, self.DESCRIPTOR_UUID, ["read"], characteristic
        )

        """
        <Field name="Report ID">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>0</Minimum>
            <Maximum>255</Maximum>
        </Field>
        
        <Field name="Report Type">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>1</Minimum>
            <Maximum>3</Maximum>
            <Enumerations>
                <Enumeration value="Input Report" key="1"/>
                <Enumeration value="Output report" key="2"/>
                <Enumeration value="Feature Report" key="3"/>
                <ReservedForFutureUse start="4" end="255"/>
                <ReservedForFutureUse1 start1="0" end1="0"/>
            </Enumerations>
        </Field>
        """

        # This report uses ReportId 2 as defined in the ReportMap characteristic
        self.value = dbus.Array(
            bytearray.fromhex("0201"), signature=dbus.Signature("y")
        )
        print(f"***ReportReference***: {self.value}")

    def ReadValue(self, options):
        print(f"Read ReportReference: {self.value}")
        return self.value
