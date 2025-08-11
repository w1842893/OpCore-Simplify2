from Scripts.datasets.mac_model_data import mac_devices
from Scripts.datasets import kext_data
from Scripts.datasets import os_data
from Scripts import gathering_files
from Scripts import run
from Scripts import utils
import os
import uuid
import random

class SMBIOS:
    def __init__(self):
        self.g = gathering_files.gatheringFiles()
        self.run = run.Run().run
        self.utils = utils.Utils()
        self.script_dir = os.path.dirname(os.path.realpath(__file__))

    def check_macserial(self):
        macserial_name = "macserial.exe" if os.name == "nt" else "macserial"
        macserial_path = os.path.join(self.script_dir, macserial_name)

        if not os.path.exists(macserial_path):
            download_history = self.utils.read_file(self.g.download_history_file)

            if download_history:
                product_index = self.g.get_product_index(download_history, "OpenCorePkg")
                
                if product_index:
                    download_history.pop(product_index)
                    self.utils.write_file(self.g.download_history_file, download_history)

            self.g.gather_bootloader_kexts([], "")
            return self.check_macserial()
        
        return macserial_path

    def generate_random_mac(self):
        random_mac = ''.join([format(random.randint(0, 255), '02X') for _ in range(6)])
        return random_mac

    def generate_smbios(self, smbios_model):
        macserial = self.check_macserial()

        random_mac_address = self.generate_random_mac()

        output = self.run({
            "args":[macserial, "-g", "--model", smbios_model]
        })
        
        if output[-1] != 0 or not " | " in output[0]:
            serial = []
        else:
            serial = output[0].splitlines()[0].split(" | ")

        return {
            "MLB": "A" + "0"*15 + "Z" if not serial else serial[-1],
            "ROM": random_mac_address,
            "SystemProductName": smbios_model,
            "SystemSerialNumber": "A" + "0"*10 + "9" if not serial else serial[0],
            "SystemUUID": str(uuid.uuid4()).upper(),
        }
    
    def smbios_specific_options(self, hardware_report, smbios_model, macos_version, acpi_patches, kext_maestro):
        for patch in acpi_patches:
            if patch.name == "MCHC":
                patch.checked = "Intel" in hardware_report.get("CPU").get("Manufacturer") and not "MacPro" in smbios_model

        selected_kexts = []

        if "MacPro7,1" in smbios_model:
            selected_kexts.append("RestrictEvents")

        if smbios_model in (device.name for device in mac_devices[31:34] + mac_devices[48:50] + mac_devices[51:61]):
            selected_kexts.append("NoTouchID")

        for name in selected_kexts:
            kext_maestro.check_kext(kext_data.kext_index_by_name.get(name), macos_version, "Beta" in os_data.get_macos_name_by_darwin(macos_version))
    
    def select_smbios_model(self, hardware_report, macos_version):
        platform = "NUC" if "NUC" in hardware_report.get("Motherboard").get("Name") else hardware_report.get("Motherboard").get("Platform")
        codename = hardware_report.get("CPU").get("Codename")

        smbios_model = "MacBookPro16,3" if "Laptop" in platform else "iMacPro1,1" if self.utils.parse_darwin_version(macos_version) < self.utils.parse_darwin_version("25.0.0") else "MacPro7,1"

        if codename in ("Lynnfield", "Clarkdale") and "Xeon" not in hardware_report.get("CPU").get("Processor Name") and self.utils.parse_darwin_version(macos_version) < self.utils.parse_darwin_version("19.0.0"):
            smbios_model = "iMac11,1" if codename in "Lynnfield" else "iMac11,2"
        elif codename in ("Beckton", "Westmere-EX", "Gulftown", "Westmere-EP", "Clarkdale", "Lynnfield", "Jasper Forest", "Gainestown", "Bloomfield"):
            smbios_model = "MacPro5,1" if self.utils.parse_darwin_version(macos_version) < self.utils.parse_darwin_version("19.0.0") else "MacPro6,1"
        elif ("Sandy Bridge" in codename or "Ivy Bridge" in codename) and self.utils.parse_darwin_version(macos_version) < self.utils.parse_darwin_version("22.0.0"):
            smbios_model = "MacPro6,1"

        if platform != "Laptop" and list(hardware_report.get("GPU").items())[-1][-1].get("Device Type") != "Integrated GPU":
            return smbios_model
        
        if codename in ("Arrandale", "Clarksfield"):
            smbios_model = "MacBookPro6,1"
        elif "Sandy Bridge" in codename:
            if "Desktop" in platform:
                smbios_model = "iMac12,2"
            elif "NUC" in platform:
                smbios_model = "Macmini5,1" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "Macmini5,3"
            elif "Laptop" in platform:
                smbios_model = "MacBookPro8,1" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "MacBookPro8,2"
        elif "Ivy Bridge" in codename:
            if "Desktop" in platform:
                smbios_model = "iMac13,1" if "Integrated GPU" in list(hardware_report.get("GPU").items())[0][-1].get("Device Type") else "iMac13,2"
            elif "NUC" in platform:
                smbios_model = "Macmini6,1" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "Macmini6,2"
            elif "Laptop" in platform:
                smbios_model = "MacBookPro10,2" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "MacBookPro10,1"
        elif "Haswell" in codename:
            if "Desktop" in platform:
                smbios_model = "iMac14,4" if "Integrated GPU" in list(hardware_report.get("GPU").items())[0][-1].get("Device Type") else "iMac15,1"
            elif "NUC" in platform:
                smbios_model = "Macmini7,1"
            elif "Laptop" in platform:
                smbios_model = "MacBookPro11,1" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "MacBookPro11,5"
        elif "Broadwell" in codename:
            if "Desktop" in platform:
                smbios_model = "iMac16,2" if "Integrated GPU" in list(hardware_report.get("GPU").items())[0][-1].get("Device Type") else "iMac17,1"
            elif "NUC" in platform:
                smbios_model = "iMac16,1"
            elif "Laptop" in platform:
                smbios_model = "MacBookPro12,1" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "MacBookPro11,5"
        elif "Skylake" in codename:
            smbios_model = "iMac17,1"
            if "Laptop" in platform:
                smbios_model = "MacBookPro13,1" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "MacBookPro13,3"
        elif "Amber Lake" in codename or "Kaby Lake" in codename:
            smbios_model = "iMac18,1" if "Integrated GPU" in list(hardware_report.get("GPU").items())[0][-1].get("Device Type") else "iMac18,3"
            if "Laptop" in platform:
                smbios_model = "MacBookPro14,1" if int(hardware_report.get("CPU").get("Core Count")) < 4 else "MacBookPro14,3"
        elif "Cannon Lake" in codename or "Whiskey Lake" in codename or "Coffee Lake" in codename or "Comet Lake" in codename:
            smbios_model = "Macmini8,1"
            if "Desktop" in platform:
                smbios_model = "iMac18,3" if self.utils.parse_darwin_version(macos_version) < self.utils.parse_darwin_version("18.0.0") else "iMac19,1"
                if "Comet Lake" in codename:
                    smbios_model = "iMac20,1" if int(hardware_report.get("CPU").get("Core Count")) < 10 else "iMac20,2"
            elif "Laptop" in platform:
                if "-8" in hardware_report.get("CPU").get("Processor Name"):
                    smbios_model = "MacBookPro15,2" if int(hardware_report.get("CPU").get("Core Count")) < 6 else "MacBookPro15,3"
                else:
                    smbios_model = "MacBookPro16,3" if int(hardware_report.get("CPU").get("Core Count")) < 6 else "MacBookPro16,1"
        elif "Ice Lake" in codename:
            smbios_model = "MacBookAir9,1"

        return smbios_model
    
    def customize_smbios_model(self, hardware_report, selected_smbios_model, macos_version):
        current_category = None
        default_smbios_model = self.select_smbios_model(hardware_report, macos_version)

        while True:
            contents = []
            contents.append("")
            contents.append("List of available SMBIOS:")
            for index, device in enumerate(mac_devices, start=1):
                category = ""
                for char in device.name:
                    if char.isdigit():
                        break
                    category += char
                if category != current_category:
                    current_category = category
                    category_header = "Category: {}".format(current_category if current_category else "Uncategorized")
                    contents.append(f"\n{category_header}\n" + "=" * len(category_header))
                checkbox = "[*]" if device.name == selected_smbios_model else "[ ]"
                
                line = "{} {:2}. {:15} - {:10} {:20}{}".format(checkbox, index, device.name, device.cpu, "({})".format(device.cpu_generation), "" if not device.discrete_gpu else " - {}".format(device.discrete_gpu))
                if device.name == selected_smbios_model:
                    line = "\033[1;32m{}\033[0m".format(line)
                elif not self.utils.parse_darwin_version(device.initial_support) <= self.utils.parse_darwin_version(macos_version) <= self.utils.parse_darwin_version(device.last_supported_version):
                    line = "\033[90m{}\033[0m".format(line)
                contents.append(line)
            contents.append("\033[1;36m")
            contents.append("Note:")
            contents.append("- Lines in gray indicate mac models that are not supported by the current macOS version ({}).".format(macos_version))
            contents.append("- You can select mac model by entering their index or name.")
            contents.append("\033[0m")
            if selected_smbios_model != default_smbios_model:
                contents.append("R. Restore default SMBIOS model ({})".format(default_smbios_model))
                contents.append("") 
            contents.append("B. Back")
            contents.append("Q. Quit")
            contents.append("")
            content = "\n".join(contents)

            self.utils.adjust_window_size(content)
            self.utils.head("Customize SMBIOS Model", resize=False)
            print(content)
            option = self.utils.request_input("Select your option: ")
            if option.lower() == "q":
                self.utils.exit_program()
            if option.lower() == "b":
                return selected_smbios_model
            if option.lower() == "r" and selected_smbios_model != default_smbios_model:
                return default_smbios_model
            
            if option.strip().isdigit():
                index = int(option) - 1
                if index >= 0 and index < len(mac_devices):
                    return mac_devices[index].name
            else:
                for device in mac_devices:
                    if option.lower() == device.name.lower():
                        return device.name