import asyncio
import logging
from typing import List
from beanie import init_beanie
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from settings import Settings, get_settings
from motor.motor_asyncio import AsyncIOMotorClient

from shared.models.station_data import StationData
from shared.models.visit_counter import DailyVisitCounter, VisitCounter
from models import (
    User as SQLUser,
    Building as SQLBuilding,
    ExtData as SQLExtData,
    Station as SQLStation,
    StationData as SQLStationData,
    Bot as SQLBot,
    AllowedChat as SQLAllowedChat,
    ChatRequest as SQLChatRequest,
    Message as SQLMessage,
    VisitCounter as SQLVisitCounter,
    DailyVisitCounter as SQLDailyVisitCounter,
    DashboardConfig as SQLDashboardConfig
)

from shared.models import (
    User,
    Building,
    ExtData,
    Station,
    Bot,
    AllowedChat,
    ChatRequest,
    Message,
    DashboardConfig,
)

settings: Settings = get_settings()

engine_sql = create_engine(settings.SQLITE_URI, echo=False)
Session = sessionmaker(bind=engine_sql)

mongo_client = AsyncIOMotorClient(str(settings.MONGO_URI))

# Mapping from old SQLite IDs to new MongoDB IDs
id_maps = {
    "users": {},
    "stations": {},
    "bots": {},
    "buildings": {},
    "messages": {},
}

logger = logging.getLogger(__name__)

async def init():
    await init_beanie(
        database=mongo_client[settings.MONGO_DB],
        document_models=[
            User,
            ExtData,
            Station,
            StationData,
            Building,
            Bot,
            AllowedChat,
            ChatRequest,
            Message,
            VisitCounter,
            DailyVisitCounter,
            DashboardConfig,
        ]
    )


async def migrate_users(session):
    logger.info("Migrating Users...")
    users = session.query(SQLUser).all()
    for u in users:
        m = User(
            name                   = u.name,
            password               = u.password,
            is_active              = u.is_active,
            is_reporter            = u.is_reporter,
            api_key                = u.api_key,
            password_reset_token   = u.password_reset_token,
            reset_token_expiration = u.reset_token_expiration,
        )
        await m.insert()
        id_maps["users"][u.id] = m.id
    logger.info(f"  Migrated {len(users)} users")


async def migrate_ext_data(session):
    logger.info("Migrating ExtData...")
    ext_data: SQLExtData = session.query(SQLExtData).all()
    for row in ext_data:
        user_id = id_maps["users"][row.user.id]
        if user_id is None:
            logger.warning(f"  !! Missing User {row.user}, skipping ExtData {row.id}")
        m = ExtData(
            grid_state  = row.grid_state,
            user_id     = user_id,
            received_at = row.received_at
        )
        await m.insert()
    logger.info(f"  Migrated {len(ext_data)} ExtData records")

async def migrate_stations(session):
    logger.info("Migrating Stations...")
    stations = session.query(SQLStation).all()
    for s in stations:
        m = Station(
            station_id                = s.station_id,
            station_name              = s.station_name,
            location_lat              = s.location_lat,
            location_lng              = s.location_lng,
            location_address          = s.location_address,
            region_nation_id          = s.region_nation_id,
            region_timezone           = s.region_timezone,
            grid_interconnection_type = s.grid_interconnection_type,
            installed_capacity        = s.installed_capacity,
            start_operating_time      = s.start_operating_time,
            created_date              = s.created_date,
            last_update_time          = s.last_update_time,
            connection_status         = s.connection_status,
            contact_phone             = s.contact_phone,
            owner_name                = s.owner_name,
            generation_power          = s.generation_power,
            battery_capacity          = s.battery_capacity,
            order                     = s.order,
            enabled                   = s.enabled,
        )
        await m.insert()
        id_maps["stations"][s.id] = m.id
    logger.info(f"  Migrated {len(stations)} stations")


async def migrate_station_data(session):
    logger.info("Migrating StationData...")
    station_data =  session.query(SQLStationData).all()
    for row in station_data:
        station_id = id_maps["stations"][int(row.station_id)]
        if not station_id:
            logger.warning(f"  !! Missing Station {row.station_id}, skipping StationData {row.id}")
            continue

        m = StationData(
            station_id          = station_id,
            battery_power       = row.battery_power,
            battery_soc         = row.battery_soc,
            charge_power        = row.charge_power,
            code                = row.code,
            consumption_power   = row.consumption_power,
            discharge_power     = row.discharge_power,
            generation_power    = row.generation_power,
            grid_power          = row.grid_power,
            irradiate_intensity = row.irradiate_intensity,
            last_update_time    = row.last_update_time,
            msg                 = row.msg,
            purchase_power      = row.purchase_power,
            request_id          = row.request_id,
            wire_power          = row.wire_power,
        )
        await m.insert()
    logger.info(f"  Migrated {len(station_data)} StationData records")


async def migrate_buildings(session):
    logger.info("Migrating Buildings...")
    mongo_stations = {str(s.id): s for s in await Station.find_all().to_list()}
    mongo_users = {str(u.id): u for u in await User.find_all().to_list()}

    for row in session.query(SQLBuilding).all():
        station = None
        if row.station_id:
            mongo_id = id_maps["stations"][row.station_id]
            station = mongo_stations.get(str(mongo_id))

        mongo_user_id = str(id_maps["users"][row.report_user_id])
        report_user = mongo_users.get(mongo_user_id)
        if not report_user:
            logger.warning(f"  !! Missing user {row.report_user_id}, skipping Building {row.id}")
            continue

        m = Building(
            name        = row.name,
            color       = row.color,
            station     = station,
            report_user = report_user,
        )
        await m.insert()
        logger.info(f"  Migrated building {row.id}")
    logger.info("  Done buildings")


async def migrate_bots(session):
    logger.info("Migrating Bots...")
    bots = session.query(SQLBot).all()
    for b in bots:
        m = Bot(
            token        = b.bot_token,
            enabled      = b.enabled,
            hook_enabled = False,
        )
        await m.insert()
        id_maps["bots"][b.id] = m.id
    logger.info(f"  Migrated {len(bots)} bots")


async def migrate_allowed_chats(session):
    logger.info("Migrating AllowedChats...")
    mongo_bots = {str(b.id): b for b in await Bot.find_all().to_list()}
    chats = session.query(SQLAllowedChat).all()
    for c in chats:
        bot = mongo_bots.get(str(id_maps["bots"][c.bot_id]))
        m = AllowedChat(
            chat_id      = c.chat_id,
            bot          = bot,
            approve_date = c.approve_date,
        )
        await m.insert()
    logger.info(f"  Migrated {len(chats)} allowed chats")


async def migrate_chat_requests(session):
    logger.info("Migrating ChatRequests...")
    mongo_bots = {str(b.id): b for b in await Bot.find_all().to_list()}
    requests = session.query(SQLChatRequest).all()
    for r in requests:
        bot = mongo_bots.get(str(id_maps["bots"][r.bot_id]))
        m = ChatRequest(
            chat_id      = r.chat_id,
            bot          = bot,
            request_date = r.request_date,
        )
        await m.insert()
    logger.info(f"  Migrated {len(requests)} chat requests")


async def migrate_messages(session):
    logger.info("Migrating Messages...")
    mongo_stations = {str(s.id): s for s in await Station.find_all().to_list()}
    mongo_bots = {str(b.id): b for b in await Bot.find_all().to_list()}
    messages = session.query(SQLMessage).all()
    for msg in messages:
        bot = mongo_bots.get(str(id_maps["bots"][msg.bot_id]))
        msg_stations = [mongo_stations.get(str(id_maps["stations"][s.id])) for s in msg.stations]
        m = Message(
            channel_id           = msg.channel_id,
            name                 = msg.name,
            message_template     = msg.message_template,
            should_send_template = msg.should_send_template,
            timeout_template     = msg.timeout_template,
            bot                  = bot,
            last_sent_time       = msg.last_sent_time,
            enabled              = False,
            stations             = msg_stations,
        )
        await m.insert()
        id_maps["messages"][msg.id] = m.id
    logger.info(f"  Migrated {len(messages)} messages")


async def migrate_visit_counters(session):
    logger.info("Migrating VisitCounters...")
    counters = session.query(SQLVisitCounter).all()
    for c in counters:
        m = VisitCounter(
            visits_count = c.count
        )
        await m.insert()
    logger.info(f"  Migrated {len(counters)} VisitCounters")


async def migrate_daily_visit_counters(session):
    logger.info("Migrating DailyVisitCounters...")
    daily_counters = session.query(SQLDailyVisitCounter).all()
    for c in daily_counters:
        m = DailyVisitCounter(
            date         = c.date,
            visits_count = c.count
        )
        await m.insert()
    logger.info(f"  Migrated {len(daily_counters)} DailyVisitCounters")


async def migrate_dashboard_config(session):
    logger.info("Migrating DashboardConfig...")
    rows: List[SQLDashboardConfig] = session.query(SQLDashboardConfig).all()

    config_map = {r.key: r.value for r in rows}

    title = config_map.get("title", "")

    enable_str = config_map.get("enableOutagesSchedule", config_map.get("enable_outages_schedule", "false"))
    enable_outages = True if str(enable_str).lower() == "true" else False

    outages_queue = config_map.get("outagesScheduleQueue", config_map.get("outages_schedule_queue"))

    m = DashboardConfig(
        title                   = title,
        enable_outages_schedule = enable_outages,
        outages_schedule_queue  = outages_queue,
    )
    await m.insert()

    logger.info(f"  Migrated DashboardConfig ({m})")

async def main():
    session = Session()
    await init()
    await migrate_users(session)
    await migrate_ext_data(session)
    await migrate_stations(session)
    await migrate_station_data(session)
    await migrate_buildings(session)
    await migrate_bots(session)
    await migrate_allowed_chats(session)
    await migrate_chat_requests(session)
    await migrate_messages(session)
    await migrate_visit_counters(session)
    await migrate_daily_visit_counters(session)
    await migrate_dashboard_config(session)

    logger.info("Migration completed!")


if __name__ == "__main__":
    asyncio.run(main())
