# OpenRouteService Integration Architecture

## Overview

The OpenRouteService integration is a **service-only** Home Assistant custom component that provides route planning capabilities using the OpenRouteService API. Unlike traditional integrations with sensors and coordinators, this integration follows a minimal API consumption pattern by only calculating routes when explicitly requested through service calls.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Home Assistant"
        UI[Config Flow UI]
        Services[Service Registry]
        Automations[Automations/Scripts]
    end

    subgraph "OpenRouteService Integration"
        Init[__init__.py<br/>Entry Setup & Service Registration]
        ConfigFlow[config_flow.py<br/>Configuration Flow]
        API[api.py<br/>API Client Wrapper]
        Const[const.py<br/>Constants]
    end

    subgraph "External Services"
        ORS[OpenRouteService API]
        Pelias[Pelias Geocoding API]
    end

    UI --> ConfigFlow
    ConfigFlow --> API
    Automations --> Services
    Services --> Init
    Init --> API
    API --> ORS
    API --> Pelias

    style Init fill:#e1f5ff
    style API fill:#fff4e1
    style ConfigFlow fill:#f0e1ff
```

## Component Structure

### File Organization

```
custom_components/openrouteservice/
├── __init__.py          # Integration entry point, service registration
├── manifest.json        # Integration metadata
├── const.py            # Constants and configuration
├── config_flow.py      # UI configuration flow
├── api.py              # Async API client wrapper
├── services.yaml       # Service documentation
└── translations/
    └── en.json         # English translations
```

### Component Relationships

```mermaid
classDiagram
    class ConfigEntry {
        +str entry_id
        +dict data
        +dict options
    }

    class OpenRouteServiceAPI {
        +HomeAssistant hass
        +str api_key
        +Client _client
        +validate_api_key()
        +geocode_address(address)
        +get_directions(origin, dest, profile)
    }

    class ConfigFlow {
        +async_step_user()
        +validate API key
        +create entry
    }

    class ServiceRegistry {
        +plan_route service
    }

    ConfigFlow --> OpenRouteServiceAPI : validates with
    ConfigEntry --> OpenRouteServiceAPI : stores
    ServiceRegistry --> OpenRouteServiceAPI : calls
```

## Service Call Flow

### Route Planning Service

```mermaid
sequenceDiagram
    participant User
    participant HA as Home Assistant
    participant Service as plan_route Handler
    participant API as OpenRouteServiceAPI
    participant Pelias as Pelias Geocoding
    participant ORS as OpenRouteService API

    User->>HA: Call openrouteservice.plan_route
    HA->>Service: handle_plan_route(call)

    Note over Service: Extract origin & destination addresses

    Service->>API: geocode_address(origin)
    API->>Pelias: pelias_search(text=origin)
    Pelias-->>API: {features: [{coordinates}]}
    API-->>Service: (lon, lat)

    Service->>API: geocode_address(destination)
    API->>Pelias: pelias_search(text=destination)
    Pelias-->>API: {features: [{coordinates}]}
    API-->>Service: (lon, lat)

    Service->>API: get_directions(origin_coords, dest_coords, profile)
    API->>ORS: POST /v2/directions/{profile}
    ORS-->>API: GeoJSON route response
    API-->>Service: {summary, geometry, segments}

    Service-->>HA: Return route data
    HA-->>User: Response with distance, duration, geometry
```

## Data Flow

### Configuration Setup Flow

```mermaid
stateDiagram-v2
    [*] --> UserInput: User adds integration
    UserInput --> ValidateKey: Enter API key
    ValidateKey --> CheckUnique: API validates
    CheckUnique --> CreateEntry: Unique key
    CreateEntry --> RegisterService: Entry created
    RegisterService --> [*]: Ready

    ValidateKey --> ShowError: Invalid/Timeout
    ShowError --> UserInput: Retry
    CheckUnique --> ShowError: Duplicate
```

### Service Execution Flow

```mermaid
flowchart TD
    Start([Service Called]) --> Extract[Extract Parameters<br/>origin, destination, profile]
    Extract --> GeoOrigin[Geocode Origin Address]
    GeoOrigin --> GeoOriginCheck{Success?}
    GeoOriginCheck -->|No| ErrorOrigin[Raise: Failed to geocode origin]
    GeoOriginCheck -->|Yes| GeoDest[Geocode Destination Address]

    GeoDest --> GeoDestCheck{Success?}
    GeoDestCheck -->|No| ErrorDest[Raise: Failed to geocode destination]
    GeoDestCheck -->|Yes| CalcRoute[Calculate Route<br/>with coordinates & profile]

    CalcRoute --> RouteCheck{Route Found?}
    RouteCheck -->|No| ErrorRoute[Raise: No route found]
    RouteCheck -->|Yes| BuildResponse[Build Response Data]

    BuildResponse --> ReturnCheck{return_response?}
    ReturnCheck -->|Yes| Return[Return route data]
    ReturnCheck -->|No| ReturnNone[Return None]

    Return --> End([Complete])
    ReturnNone --> End
    ErrorOrigin --> End
    ErrorDest --> End
    ErrorRoute --> End
```

## API Client Design

### Async/Sync Pattern

The OpenRouteService Python library is **synchronous**, so we use the executor pattern to wrap blocking calls:

```mermaid
graph LR
    subgraph "Async Layer"
        A[async geocode_address]
        B[async get_directions]
        C[async validate_api_key]
    end

    subgraph "Executor Bridge"
        D[hass.async_add_executor_job]
    end

    subgraph "Sync Layer"
        E[_geocode_sync]
        F[_directions_sync]
        G[_validate_sync]
    end

    subgraph "External Library"
        H[openrouteservice.Client]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    D --> F
    D --> G
    E --> H
    F --> H
    G --> H
```

**Pattern Details:**
- Every public method is `async`
- Each async method calls `hass.async_add_executor_job()` with a sync helper
- Sync helpers (`_*_sync`) do the actual blocking I/O with the library
- This keeps the Home Assistant event loop responsive

## Configuration Management

### Entry Data Structure

```mermaid
graph TB
    subgraph "ConfigEntry"
        Data[data<br/>Immutable Setup Data]
        Options[options<br/>User Preferences]
    end

    subgraph "Stored in hass.data"
        Domain[DOMAIN dict]
        EntryData[entry_id dict]
        APIClient[api: OpenRouteServiceAPI]
    end

    Data --> EntryData
    Options --> EntryData
    Domain --> EntryData
    EntryData --> APIClient
```

**Current Phase 1:**
- `data`: Contains `api_key` only
- `options`: Empty (Phase 2 will add cache config, units, etc.)

**Future Phase 2:**
- `options`: Will contain cache TTL, default units, default language, etc.

## Service-Only Design Rationale

### Traditional vs Service-Only Approach

```mermaid
graph TB
    subgraph "Traditional Integration (e.g., HERE Maps, Waze)"
        S1[Sensors Poll Periodically]
        S1 --> C1[DataUpdateCoordinator]
        C1 --> A1[API Calls Every N Minutes]
        A1 --> E1[Entity Updates]
        E1 --> ST1[State Changes]

        style A1 fill:#ffcccc
    end

    subgraph "Service-Only Approach (OpenRouteService)"
        S2[Services Called On-Demand]
        S2 --> A2[API Calls Only When Needed]
        A2 --> R2[Direct Response]

        style A2 fill:#ccffcc
    end

    Note1[High API consumption<br/>Fixed polling interval]
    Note2[Minimal API consumption<br/>Maximum flexibility]

    A1 -.-> Note1
    A2 -.-> Note2
```

**Benefits:**
1. **Minimal API Consumption**: No background polling, only on-demand
2. **Flexibility**: Addresses provided dynamically in automations
3. **Free Tier Friendly**: Critical for OpenRouteService's rate limits
4. **Simple Architecture**: No coordinator, no entities, no state management

## Error Handling Strategy

```mermaid
flowchart TD
    Start[API Call] --> Try{Try Block}

    Try -->|Success| Return[Return Data]

    Try -->|ApiError 401/403| InvalidAuth[Raise InvalidAuth]
    Try -->|ApiError Other| CannotConnect[Raise CannotConnect]
    Try -->|Timeout| CannotConnect2[Raise CannotConnect]
    Try -->|No Features| ValueError[Raise ValueError]
    Try -->|Unknown| CannotConnect3[Raise CannotConnect]

    InvalidAuth --> ConfigFlow{In Config Flow?}
    CannotConnect --> ConfigFlow
    CannotConnect2 --> ConfigFlow
    ValueError --> ServiceCall{In Service Call?}
    CannotConnect3 --> ConfigFlow

    ConfigFlow -->|Yes| ShowError[Show UI Error Message]
    ConfigFlow -->|No| HAError[Raise HomeAssistantError]
    ServiceCall --> HAError

    ShowError --> End([User Retries])
    HAError --> End2([Logged & Shown to User])
    Return --> End3([Success])
```

**Exception Hierarchy:**
- `InvalidAuth`: Invalid API key (401/403)
- `CannotConnect`: Network/API errors
- `ValueError`: Data validation errors (no geocoding results, no route)
- `HomeAssistantError`: Wrapper for service call errors

## Key Design Patterns

### 1. Single Service Registration

```mermaid
sequenceDiagram
    participant Entry1
    participant Entry2
    participant ServiceRegistry

    Entry1->>ServiceRegistry: async_setup_entry()
    ServiceRegistry->>ServiceRegistry: has_service()?
    Note right of ServiceRegistry: False
    ServiceRegistry->>ServiceRegistry: Register plan_route

    Entry2->>ServiceRegistry: async_setup_entry()
    ServiceRegistry->>ServiceRegistry: has_service()?
    Note right of ServiceRegistry: True
    ServiceRegistry->>ServiceRegistry: Skip registration

    Note over Entry1,ServiceRegistry: Both entries share the same service
```

**Implementation:**
```python
if not hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE):
    hass.services.async_register(...)
```

### 2. Coordinate Order Convention

⚠️ **Critical:** OpenRouteService uses `[longitude, latitude]` order (NOT `[latitude, longitude]`)

```mermaid
graph LR
    A[User Address] --> B[Geocoding API]
    B --> C["coordinates: [lon, lat]"]
    C --> D[Stored as tuple: lon, lat]
    D --> E[Directions API]
    E --> F["Input: [[lon1, lat1], [lon2, lat2]]"]
```

**Always:**
- Store as `(longitude, latitude)` tuples
- Convert to `[[lon, lat], [lon, lat]]` for API calls
- Never swap the order

### 3. Service Response Pattern

```python
if call.return_response:
    return {
        "origin": {...},
        "destination": {...},
        "distance": ...,
        "duration": ...,
        "geometry": ...,
        "segments": ...,
    }
return None
```

Supports `response_variable` in automations for programmatic route data access.

## Integration Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Setup: async_setup_entry()
    Setup --> ValidateClient: Create API client
    ValidateClient --> StoreData: Store in hass.data
    StoreData --> RegisterServices: Register services (if first)
    RegisterServices --> Ready: Integration Ready

    Ready --> ServiceCall: User calls service
    ServiceCall --> Ready: Service completes

    Ready --> Unload: async_unload_entry()
    Unload --> RemoveData: Remove from hass.data
    RemoveData --> CheckEntries: Other entries exist?
    CheckEntries --> UnregisterServices: No - Remove services
    CheckEntries --> Complete: Yes - Keep services
    UnregisterServices --> Complete
    Complete --> [*]
```

## Future Phase 2 Architecture

Phase 2 will add:

1. **Cache Layer** (`cache.py`)
   - Separate geocoding cache and route cache
   - Configurable TTL for each
   - Persistent storage

2. **Options Flow**
   - Cache duration configuration
   - Units (metric/imperial)
   - Language preferences

3. **Clear Cache Service**
   - Manual cache management

```mermaid
graph TB
    subgraph "Phase 2 Additions"
        Cache[cache.py<br/>Route & Geocoding Cache]
        OptionsFlow[Options Flow Handler]
        ClearCache[clear_cache Service]
    end

    Services --> Cache
    Cache --> API
    OptionsFlow --> ConfigEntry
    ClearCache --> Cache

    style Cache fill:#ffffcc
    style OptionsFlow fill:#ffffcc
    style ClearCache fill:#ffffcc
```

## Testing Architecture

```mermaid
graph TB
    subgraph "Unit Tests"
        TestAPI[test_api.py<br/>API client methods]
        TestInit[test_init.py<br/>Service registration]
        TestConfig[test_config_flow.py<br/>Configuration flow]
    end

    subgraph "Integration Tests"
        TestIntegration[test_integration.py<br/>End-to-end flows]
        TestRealAPI[test_api_real.py<br/>Real API calls]
    end

    subgraph "Mocks"
        MockClient[Mock ORS Client]
        MockResponse[Mock API Responses]
    end

    TestAPI --> MockClient
    TestInit --> MockClient
    TestConfig --> MockClient
    TestIntegration --> MockClient
    TestRealAPI --> RealAPI[Real OpenRouteService API]

    MockClient --> MockResponse
```

**Test Strategy:**
- Unit tests use mocked OpenRouteService client
- Integration tests verify complete flows with mocks
- Real API tests (manual/optional) validate against live API
- All async code tested with pytest-homeassistant-custom-component

## API Rate Limiting Strategy

OpenRouteService free tier has rate limits. Our service-only approach minimizes consumption:

```mermaid
graph LR
    subgraph "Per Service Call"
        A[1 Geocoding Call<br/>Origin]
        B[1 Geocoding Call<br/>Destination]
        C[1 Directions Call]
    end

    A --> Total[Total: 3 API Calls]
    B --> Total
    C --> Total

    Total --> Future[Phase 2: Cache reduces to ~0 calls for repeated routes]
```

**Phase 2 Caching** will drastically reduce API calls for repeated routes.

## Security Considerations

1. **API Key Storage**: Stored in ConfigEntry data (encrypted by HA)
2. **No Secrets in Logs**: API key never logged
3. **User Input Validation**: All service parameters validated with voluptuous
4. **Error Sanitization**: API errors sanitized before showing to user
5. **HTTPS Only**: All API calls over HTTPS

## Performance Characteristics

- **Service Call Latency**: ~2-5 seconds (2 geocoding + 1 routing call)
- **Memory Footprint**: Minimal (no stored state, no entities)
- **CPU Usage**: Low (I/O bound operations in executor)
- **Network**: 3 HTTPS requests per service call (Phase 1)

## Attribution Requirements

Per OpenRouteService free tier terms:

> © openrouteservice.org by HeiGIT | Map data © OpenStreetMap contributors

Documented in README and noted during configuration.

## References

- [OpenRouteService API Documentation](https://openrouteservice.org/dev/#/api-docs)
- [Home Assistant Integration Documentation](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [HACS Requirements](https://hacs.xyz/docs/publish/integration)
- Research Document: `thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md`
- Phase 1 Plan: `thoughts/shared/plans/2025-11-12-openrouteservice-phase1.md`
