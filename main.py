import os
from dotenv import find_dotenv, load_dotenv, set_key, dotenv_values
import click
import requests


class Nest(object):
    def __init__(
        self,
        PROJECT_ID: str,
        DEVICE_ID: str,
        ACCESS_TOKEN: str,
        REFRESH_TOKEN: str,
        OAUTH2_CLIENT_ID: str,
        OAUTH2_CLIENT_SECRET: str,
    ):
        # HTTP request variables
        self.end_point = "https://smartdevicemanagement.googleapis.com/v1"
        self.call = f"enterprises/{PROJECT_ID}/devices/{DEVICE_ID}"
        self.url = f"{self.end_point}/{self.call}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ACCESS_TOKEN}",
        }

        # oauth2 variables
        self.oauth2_url = "https://www.googleapis.com/oauth2/v4/token"
        self.oauth2_data = {
            "client_id": OAUTH2_CLIENT_ID,
            "client_secret": OAUTH2_CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
        }

    def refresh_access_token(self) -> None:
        """Refresh the access token"""
        try:
            r = requests.post(url=self.oauth2_url, data=self.oauth2_data)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            raise SystemExit("Error: One or more credentials are invalid. A common cause is the refresh token becoming invalid.")

        # Update access token in headers
        response = r.json()
        access_token = response["access_token"]
        self.headers["Authorization"] = f"Bearer {access_token}"

        # Update environment variable
        dotenv_path = find_dotenv(".env")
        set_key(dotenv_path, "ACCESS_TOKEN", access_token)

        return None

    def fetch_device_traits(self) -> dict[str, any]:
        """Fetch all available device traits"""
        # TODO: Duplicated code, find a more elegant solution
        try:
            r = requests.get(url=self.url, headers=self.headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            # Anauthorized error (401), attempt to refresh access token
            self.refresh_access_token()
            try:
                r = requests.get(url=self.url, headers=self.headers)
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)

        # extracting data in json format
        response = r.json()
        traits = response["traits"]
        return traits

    def send_device_command(self, payload: dict[str, any]) -> None:
        """Send command, included in payload, to the device"""
        # TODO: Duplicated code, find a more elegant solution
        try:
            r = requests.post(
                url=f"{self.url}:executeCommand", headers=self.headers, json=payload
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            # Aunauthorized error (401), attempt to refresh access token
            self.refresh_access_token()
            try:
                r = requests.post(
                    url=f"{self.url}:executeCommand", headers=self.headers, json=payload
                )
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
        return None

    def get_ambient_humidity_percent(self, traits: dict[str, any] = None) -> int:
        """Get the ambient humidity percentage"""
        # If traits are not provided, fetch them
        if traits is None:
            traits = self.fetch_device_traits()

        # Extract desired trait
        humidity_trait = traits["sdm.devices.traits.Humidity"]
        ambient_humidity_percent = humidity_trait["ambientHumidityPercent"]
        return ambient_humidity_percent

    def get_ambient_temperature_celsius(self, traits: dict[str, any] = None) -> float:
        """Get the ambient temperature measured in celsius"""
        # If traits are not provided, fetch them
        if traits is None:
            traits = self.fetch_device_traits()

        # Extract desired trait
        temperature_trait = traits["sdm.devices.traits.Temperature"]
        ambient_temperature_celsius = temperature_trait["ambientTemperatureCelsius"]
        return ambient_temperature_celsius

    def get_temperature_setpoint(self, traits: dict[str, any] = None) -> float:
        """Get the current temperature setpoint in celsius"""
        # If traits are not provided, fetch them
        if traits is None:
            traits = self.fetch_device_traits()

        # Extract desired trait
        setpoint_trait = traits["sdm.devices.traits.ThermostatTemperatureSetpoint"]
        temperature_setpoint = setpoint_trait["heatCelsius"]
        return temperature_setpoint

    def get_mode(self, traits: dict[str, any] = None) -> str:
        """Get the current temperature setpoint in celsius"""
        # If traits are not provided, fetch them
        if traits is None:
            traits = self.fetch_device_traits()

        # Extract thermostat mode
        mode_trait = traits["sdm.devices.traits.ThermostatMode"]
        mode = mode_trait["mode"]
        
        # Extract thermostat eco mode
        eco_trait = traits["sdm.devices.traits.ThermostatEco"]
        eco_mode = eco_trait["mode"]
        
        # Override mode if eco is turned on
        if eco_mode == "MANUAL_ECO":
            mode = "MANUAL_ECO"
        
        return mode
    
    def set_temperature_setpoint(self, value: float) -> None:
        """Set the temperature setpoint in celsius"""
        # TODO: "400 client Error" if mode OFF or MANUAL_ECO
        payload = {
            "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
            "params": {"heatCelsius": value},
        }
        self.send_device_command(payload)
        return None
    
    def set_mode(self, mode: str) -> None:
        """Set the thermostat mode"""
        
        # Create payload depending on mode type
        if mode == "MANUAL_ECO":
            payload = {
                "command": "sdm.devices.commands.ThermostatEco.SetMode",
                "params": {"mode": "MANUAL_ECO"},
            }
        else:
            payload = {
                "command": "sdm.devices.commands.ThermostatMode.SetMode",
                "params": {"mode": mode},
            }
            
        self.send_device_command(payload)
        return None


@click.group()
@click.version_option("0.1.0", prog_name="NestPy")
@click.pass_context
def cli(ctx) -> None:
    # Check if .env file exists
    found_dotenv = load_dotenv()
    if not found_dotenv:
        if ctx.invoked_subcommand != 'config':
            raise SystemExit("No config file has been found, see 'nestpy config --help'")
        return None
     
    
    # Load .env variables
    dotenv_path = find_dotenv()
    env_vars = dotenv_values(dotenv_path)
    
    # Create Nest object
    try:
        ctx.obj = Nest(**env_vars)
    except TypeError as err:
        # Notify the user to configure missing options when using any command other than 'config'.
        if ctx.invoked_subcommand == 'config':
            return None
        # Modify error message
        err_str = str(err)
        missing_args = err_str.split(': ')[1].lower().replace('_', '-')
        msg = f"Please configure the missing options: {missing_args}"
        raise SystemExit(msg)
        
            

    return None


@cli.command("set")
@click.option(
    "-t", "--temperature", type=click.FLOAT, help="set the temperature setpoint"
)
@click.pass_obj
def set_trait(nest, temperature) -> None:
    # TODO: Decide if to merge set_mode with set_trait
    if temperature:
        nest.set_temperature_setpoint(temperature)
    return None


@cli.command("get")
@click.option("-h", "--humidity", is_flag=True, help="get ambient humidity percent")
@click.option("-t", "--temperature", is_flag=True, help="get ambient temperature")
@click.option("-s", "--setpoint", is_flag=True, help="get temperature setpoint")
@click.option("-m", "--mode", is_flag=True, help="get thermostat mode")
@click.pass_obj
def get_trait(nest, humidity, temperature, setpoint, mode) -> None:
    traits = nest.fetch_device_traits()
    output = ""
    if humidity:
        humidity_value = nest.get_ambient_humidity_percent(traits)
        output += f"{humidity_value} "
    if temperature:
        temperature_value = nest.get_ambient_temperature_celsius(traits)
        output += f"{temperature_value} "
    if setpoint:
        setpoint_value = nest.get_temperature_setpoint(traits)
        output += f"{setpoint_value} "
    if mode:
        mode_value = nest.get_mode(traits)
        output += f"{mode_value}"
    click.echo(output.strip())

    return None


@cli.command("mode")
@click.option("-o", "--off", is_flag=True, help="set thermostat mode to OFF")
@click.option("-e", "--eco", is_flag=True, help="set thermostat mode to ECO")
@click.option("-h", "--heat", is_flag=True, help="set thermostat mode to HEAT")
@click.pass_obj
def set_mode(nest, off, heat, eco) -> None:
    # TODO: Decided what to do when multiple flag are given
    if off:
        nest.set_mode(mode="OFF")
    elif eco:
        nest.set_mode(mode="MANUAL_ECO")
    else: # heat
        nest.set_mode(mode="HEAT")
    return None


@cli.command("config")
@click.option("--project-id", type=click.STRING, default=None)
@click.option("--device-id", type=click.STRING, default=None)
@click.option("--access-token", type=click.STRING, default=None)
@click.option("--refresh-token", type=click.STRING, default=None)
@click.option("--oauth2-client-id", type=click.STRING, default=None)
@click.option("--oauth2-client-secret", type=click.STRING, default=None)
def config(project_id, device_id, access_token, refresh_token, oauth2_client_id, oauth2_client_secret) -> None:
    # Define the .env path in the package directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    dotenv_path = os.path.join(script_dir, ".env")

    # Define a dictionary to map arguments to keys
    key_mapping = {
        "PROJECT_ID": project_id,
        "DEVICE_ID": device_id,
        "ACCESS_TOKEN": access_token,
        "REFRESH_TOKEN": refresh_token,
        "OAUTH2_CLIENT_ID": oauth2_client_id,
        "OAUTH2_CLIENT_SECRET": oauth2_client_secret
    }

    # Iterate over the dictionary and set key values if the argument is not None
    for key, value in key_mapping.items():
        if value is not None:
            set_key(dotenv_path, key, value)

    return None


if __name__ == "__main__":
    cli()
