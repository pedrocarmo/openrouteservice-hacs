# OpenRouteService Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/pedrocarmo/open-route-service-hacs.svg)](https://github.com/pedrocarmo/open-route-service-hacs/releases)
[![License](https://img.shields.io/github/license/pedrocarmo/open-route-service-hacs.svg)](LICENSE)

A Home Assistant custom component that provides route planning services using [OpenRouteService](https://openrouteservice.org/), a free routing service based on OpenStreetMap data.

## Features

- 🚗 **Service-only architecture** - No sensors, minimal API consumption
- 📍 **Automatic address geocoding** - Use addresses directly, no need for coordinates
- 🗺️ **Multiple transportation modes** - Driving, cycling, walking, wheelchair, and HGV
- ⚡ **Route optimization** - Choose fastest, shortest, or recommended routes
- 🤖 **Automation-friendly** - Returns comprehensive route data for use in automations
- 🔄 **Zero polling** - Routes calculated only when you request them

## What Makes This Different?

Unlike other mapping integrations (HERE Maps, Google Maps, Waze) that use sensors and constantly poll for updates, this integration uses a **service-only approach**:

- **No background polling** - Routes calculated only when you call the service
- **Lower API consumption** - Perfect for free tier API limits
- **Maximum flexibility** - Specify addresses dynamically in each automation
- **Fresh data on demand** - Get up-to-date routes when you need them

## Installation

### Prerequisites

1. **Get an API key** from [OpenRouteService](https://openrouteservice.org/sign-up/) (free tier available)
2. Home Assistant 2024.1.0 or newer

### Method 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/pedrocarmo/open-route-service-hacs`
6. Select category: "Integration"
7. Click "Add"
8. Find "OpenRouteService" in HACS and install it
9. Restart Home Assistant

### Method 2: Manual Installation

1. Copy the `custom_components/openrouteservice` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

Your directory structure should look like:
```
config/
├── configuration.yaml
└── custom_components/
    └── openrouteservice/
        ├── __init__.py
        ├── api.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        ├── services.yaml
        └── translations/
            └── en.json
```

## Configuration

### Add Integration via UI

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION** (bottom right)
3. Search for "OpenRouteService"
4. Enter your API key
5. Click **Submit**

The integration will validate your API key before completing setup.

## Usage

### Service: `openrouteservice.plan_route`

Plan a route between two addresses.

#### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `origin` | Yes | - | Starting address (automatically geocoded) |
| `destination` | Yes | - | Destination address (automatically geocoded) |
| `profile` | No | `driving-car` | Transportation mode |
| `preference` | No | `fastest` | Route optimization preference |

#### Transportation Modes (`profile`)

- `driving-car` - Standard car routing
- `driving-hgv` - Heavy goods vehicle routing
- `cycling-regular` - Bicycle routing
- `foot-walking` - Pedestrian routing
- `wheelchair` - Wheelchair-accessible routing

#### Route Preferences (`preference`)

- `fastest` - Minimize travel time
- `shortest` - Minimize distance
- `recommended` - Balanced route

### Basic Example

```yaml
service: openrouteservice.plan_route
data:
  origin: "Brandenburg Gate, Berlin"
  destination: "Berlin Hauptbahnhof"
  profile: "driving-car"
  preference: "fastest"
```

### Automation Example

Get route information and send a notification:

```yaml
automation:
  - alias: "Morning commute check"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: openrouteservice.plan_route
        data:
          origin: "{{ states('zone.home') }}"
          destination: "{{ states('zone.work') }}"
          profile: "driving-car"
          preference: "fastest"
        response_variable: route

      - service: notify.mobile_app
        data:
          title: "Morning Commute"
          message: |
            🚗 Route to work:
            Distance: {{ (route.distance / 1000) | round(1) }} km
            Duration: {{ (route.duration / 60) | round(0) }} minutes
```

### Using Different Transportation Modes

```yaml
# Cycling route
service: openrouteservice.plan_route
data:
  origin: "Alexanderplatz, Berlin"
  destination: "Tiergarten, Berlin"
  profile: "cycling-regular"
  preference: "recommended"
```

```yaml
# Walking route
service: openrouteservice.plan_route
data:
  origin: "Museum Island, Berlin"
  destination: "Brandenburg Gate, Berlin"
  profile: "foot-walking"
  preference: "shortest"
```

### Response Data Structure

When using `response_variable`, the service returns:

```yaml
{
  "origin": {
    "address": "Brandenburg Gate, Berlin",
    "coordinates": [13.377704, 52.516275]  # [longitude, latitude]
  },
  "destination": {
    "address": "Berlin Hauptbahnhof",
    "coordinates": [13.369549, 52.525589]
  },
  "distance": 2150.5,           # meters
  "duration": 420.3,            # seconds
  "profile": "driving-car",
  "preference": "fastest",
  "geometry": {...},            # GeoJSON LineString
  "segments": [...]             # Turn-by-turn segments
}
```

### Advanced: Using Route Geometry

The `geometry` field contains a GeoJSON LineString that can be used with mapping cards:

```yaml
action:
  - service: openrouteservice.plan_route
    data:
      origin: "{{ states('zone.home') }}"
      destination: "{{ states('zone.work') }}"
    response_variable: route

  - service: input_text.set_value
    target:
      entity_id: input_text.route_geometry
    data:
      value: "{{ route.geometry | to_json }}"
```

## API Rate Limits

OpenRouteService free tier has daily request limits:

- **40 requests/minute**
- **2,000 requests/day**

Since this integration uses a service-only approach (no background polling), you have full control over API consumption. Each service call makes:
- 2 geocoding requests (origin + destination)
- 1 routing request

**Tip:** Cache frequently used routes in automations using `input_text` or `variable` helpers.

## Troubleshooting

### Integration doesn't appear in UI

1. Check logs: **Settings** → **System** → **Logs**
2. Look for errors mentioning `openrouteservice`
3. Verify file structure in `custom_components/openrouteservice/`
4. Restart Home Assistant

### "Invalid API key" error

1. Verify your API key at [OpenRouteService](https://openrouteservice.org/)
2. Check that you copied the entire key
3. Try generating a new API key

### "Could not geocode address" error

- Check address spelling and formatting
- Try more specific addresses (include city, country)
- Use landmark names or postal codes
- Example: `"Alexanderplatz 1, 10178 Berlin, Germany"`

### "No route found" error

- Verify both addresses are valid and reachable
- Check if transportation mode is appropriate (e.g., some areas may not have wheelchair-accessible routes)
- Try different route preferences

### Rate limit errors

- Reduce frequency of service calls in automations
- Consider implementing local caching
- Upgrade to OpenRouteService premium tier if needed

## Data Source & Attribution

This integration uses [OpenRouteService](https://openrouteservice.org/), which is based on [OpenStreetMap](https://www.openstreetmap.org/) data.

**Routing Information:**
- Routes are calculated using OpenStreetMap road network data
- Distance calculations are highly accurate
- Travel times are estimates based on speed limits and road types
- **Does not include real-time traffic data**

**Required Attribution:**
```
© openrouteservice.org by HeiGIT | Map data © OpenStreetMap contributors
```

When displaying routes in your Home Assistant interface, please include this attribution.

## Roadmap

### Phase 2 (Planned)
- ✨ Route caching with configurable TTL
- ⚙️ Options flow for user preferences
- 🗑️ Cache management service

### Phase 3 (Future)
- 🚧 Advanced routing parameters (avoid highways, tolls, etc.)
- 🛣️ Alternative routes support
- 📊 Route comparison features
- 🧪 Unit tests and CI/CD

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/pedrocarmo/open-route-service-hacs/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pedrocarmo/open-route-service-hacs/discussions)
- **Documentation**: [Home Assistant Community](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenRouteService](https://openrouteservice.org/) for providing the routing API
- [GIScience](https://github.com/GIScience) for the [openrouteservice-py](https://github.com/GIScience/openrouteservice-py) library
- [OpenStreetMap](https://www.openstreetmap.org/) contributors for map data
- Home Assistant community for integration patterns and best practices

---

**Made with ❤️ for the Home Assistant community**
