import os
from dotenv import load_dotenv, set_key
import click
import requests


class Nest(object):
    def __init__(self, project_id, device_id, access_token):
        # API variables
        self.project_id = project_id
        self.device_id = device_id
        self.access_token = access_token

        # HTTP request variables
        self.call = f"enterprises/{project_id}/devices/{device_id}"
        self.end_point = "https://smartdevicemanagement.googleapis.com/v1"
        self.url = f"{self.end_point}/{self.call}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        # Device variables
        self.mode = "OFF"  # {OFF, HEAT, MANUAL_ECO}

    def refresh_access_token(self) -> None:
        # TODO: Implement the refreshing and saving of the access token
        raise NotImplementedError
    
    def fetch_device_traits(self) -> dict[str, any]:
        try:
            r = requests.get(url=self.url, headers=self.headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            # self.refresh_access_token()
            raise SystemExit("Error: Invalid authentication credentials")

        # extracting data in json format
        response = r.json()
        traits = response["traits"]
        return traits

    def set_device_traits(self, payload) -> None:
        try:
            r = requests.post(
                url=f"{self.url}:executeCommand", headers=self.headers, json=payload
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            # self.refresh_access_token()
            raise SystemExit("Error: Invalid authentication credentials")
        return None

    def get_ambient_humidity_percent(self, traits: dict[str, any] = None) -> int:
        # If traits are not provided, fetch them
        if traits is None:
            traits = self.fetch_device_traits()
        # Extract desired trait
        humidity_trait = traits["sdm.devices.traits.Humidity"]
        ambient_humidity_percent = humidity_trait["ambientHumidityPercent"]
        return ambient_humidity_percent

    def get_ambient_temperature_celsius(self, traits: dict[str, any] = None) -> float:
        # If traits are not provided, fetch them
        if traits is None:
            traits = self.fetch_device_traits()
        # Extract desired trait
        temperature_trait = traits["sdm.devices.traits.Temperature"]
        ambient_temperature_celsius = temperature_trait["ambientTemperatureCelsius"]
        return ambient_temperature_celsius

    def get_temperature_setpoint(self, traits: dict[str, any] = None) -> float:
        # If traits are not provided, fetch them
        if traits is None:
            traits = self.fetch_device_traits()
        # Extract desired trait
        setpoint_trait = traits["sdm.devices.traits.ThermostatTemperatureSetpoint"]
        temperature_setpoint = setpoint_trait["heatCelsius"]
        return temperature_setpoint

    def set_temperature_setpoint(self, value: float) -> None:
        payload = {
            "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
            "params": {"heatCelsius": value},
        }
        self.set_device_traits(payload)


# def refresh_access_token():
#     refresh_token = os.environ.get("REFRESH_TOKEN")
#     print(refresh_token)
#     # raise NotImplementedError


@click.group()
@click.version_option("0.1.0", prog_name="NestPy")
@click.pass_context
def cli(ctx) -> None:
    # Load environment variables from .env file
    load_dotenv()

    # Create NestThermostat object
    ctx.obj = Nest(
        project_id=os.environ["PROJECT_ID"],
        device_id=os.environ["DEVICE_ID"],
        access_token=os.environ["ACCESS_TOKEN"],
    )

    return None


@cli.command("set")
@click.option(
    "-t", "--temperature", type=click.FLOAT, help="set the temperature setpoint"
)
@click.pass_obj
def set_trait(nest, temperature) -> None:
    nest.set_temperature_setpoint(temperature)
    return None


@cli.command("get")
@click.option("-h", "--humidity", is_flag=True, help="get ambient humidity percent")
@click.option("-t", "--temperature", is_flag=True, help="get ambient temperature")
@click.option("-s", "--setpoint", is_flag=True, help="get temperature setpoint")
@click.pass_obj
def get_trait(nest, humidity, temperature, setpoint) -> None:
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
    click.echo(output.strip())

    return None


@cli.command("mode")
@click.option("-o", "--off", is_flag=True, help="set thermostat mode to OFF")
@click.option("-h", "--heat", is_flag=True, help="set thermostat mode to HEAT")
@click.option("-e", "--eco", is_flag=True, help="set thermostat mode to ECO")
def set_mode() -> None:
    # TODO: Implement this functionality
    raise NotImplementedError


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
