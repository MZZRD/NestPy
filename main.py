import os
from dotenv import find_dotenv, load_dotenv, set_key
import click
import requests


class Nest(object):
    def __init__(
        self,
        project_id: str,
        device_id: str,
        access_token: str,
        refresh_token: str,
        oauth2_client_id: str,
        oauth2_client_secret: str,
    ):
        # HTTP request variables
        self.end_point = "https://smartdevicemanagement.googleapis.com/v1"
        self.call = f"enterprises/{project_id}/devices/{device_id}"
        self.url = f"{self.end_point}/{self.call}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        # oauth2 variables
        self.oauth2_url = "https://www.googleapis.com/oauth2/v4/token"
        self.oauth2_data = {
            "client_id": oauth2_client_id,
            "client_secret": oauth2_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

    def refresh_access_token(self) -> None:
        """Refresh the access token"""
        try:
            r = requests.post(url=self.oauth2_url, data=self.oauth2_data)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            raise SystemExit("Error: Invalid OAuth2 credentials")

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
            # Aunauthorized error (401), attempt to refresh access token
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
    # Load environment variables from .env file
    # TODO: check if .env is found
    load_dotenv()

    # Create NestThermostat object
    # TODO: Check if all env variables are configured
    ctx.obj = Nest(
        project_id=os.environ["PROJECT_ID"],
        device_id=os.environ["DEVICE_ID"],
        access_token=os.environ["ACCESS_TOKEN"],
        refresh_token=os.environ["REFRESH_TOKEN"],
        oauth2_client_id=os.environ["OAUTH2_CLIENT_ID"],
        oauth2_client_secret=os.environ["OAUTH2_CLIENT_SECRET"],
    )

    return None


@cli.command("set")
@click.option(
    "-t", "--temperature", type=click.FLOAT, help="set the temperature setpoint"
)
@click.pass_obj
def set_trait(nest, temperature) -> None:
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
def config(project_id, device_id, access_token, refresh_token) -> None:
    # Set the .env path in the package directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    dotenv_path = os.path.join(script_dir, ".env")

    # Define a dictionary to map arguments to keys
    key_mapping = {
        "PROJECT_ID": project_id,
        "DEVICE_ID": device_id,
        "ACCESS_TOKEN": access_token,
        "REFRESH_TOKEN": refresh_token,
    }

    # Iterate over the dictionary and set key values if the argument is not None
    for key, value in key_mapping.items():
        if value is not None:
            set_key(dotenv_path, key, value)

    return None


if __name__ == "__main__":
    cli()
