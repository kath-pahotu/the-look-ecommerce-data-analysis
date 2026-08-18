--02_core_dimensions

/*
1. DATE DIMENSION

create or replace the schema
create dim date:
- create datebound CTE (select min/max... from... union ) from tables stg.events, stg.order_items, stg.inventory_items, stg.inventory_events: find minimum and maximum dates
- CTE calendar: generate all dates between the boudaries, generate_series (coulms, calendar_date, nested query: column generate_series(min_date, max_date, interval 1 day) as series(value))
- calendar date, year, quarter_number, quarter_label, month_number, month_name (full), 
month_year (abb month), month_start (date_trunc), quarter_start, eyar_start, 
iso_week_number. iso_day_of_week, day_name (mon-sun), is_weekend, is_complete_month (date >  truncate monthmax date then 1 else 0 )
strftime
%Y%m%d: date key, cast as integer
%B: full Month name, %b: abb month name
%A: full day name (mon-sun)
isodow: day of week (1-7)
*/

create schema if not exists core;


create or replace table core.dim_date as
with date_bounds as(

   select 
        
    from (
        select 
            min(created_at) as date_value
        from stg.events
        union all
        select
            max(created_at)
        from stg.events
        union all
        select
            min(created_at)
        from stg.order_items
        union all
        select 
            max(created_at)
        from stg.order_items
        union all
        select
            min(created_at)
        from stg.inventory_events
        union all
        select 
            max(coalesce(sold_at, created_at))
        from stg.inventory_events
    
    )
),

calendar as (
    select 
        cast(value as DATE) as calendar_date,
        max_date
    from date_bounds,
    generate_series(
        min_date,
        max_date,
        interval 1 day
    ) as series(value)
)
select 
    cast(strftime(calendar_date, %Y%m%d) as integer) as date_key,
    calendar_date,
    extract(year from calendar_date)::integer as year,
    extract(quarter from calendar_date)::integer as quarter_number,
    'Q'|| extract(
            quarter from calendar_date
        )::integer as quarter_label,
    extract(month from calendar_date)::integer as month_number,
    strftime(calendar_date, %B) as month_name,
    strftime(calendar_date, %b%Y) as month_year,
    date_trunc('month', calendar_date)::date as month_start,
    date_trunc('quarter', calendar_date)::date as quarter_start,
    date_trunc('year', calendar_date)::date as year_start,
    extract(week from calendar_date)::integer as iso_week_number,
    extract(isodow from calendar_date):integer as iso_day_of_week,
    strftime(calendar_date, %A) as day_name,
    case when extract(isodow from calendar_date) in (6,7) then 1 else 0 end as is_weekend,
    case when calendar_date < date_trunc('month', max_date) then 1 else 0 end as is_complete_month
    from calendar;




---File 02_core_dimensions.sql


/*
2. CUSTOMER DIMENSION (core.dim_customer)
grain: one row per customer
source: stg.users

How to build:
create of replace table as
column:
- user_id
- age
- age_band (case null; <25:18-24; <35; < 45; < 55; < 65: else 65+)
- gender
- country (coalesce unknown)
- state(coalesce unknown)
- city(coalesce unknown)
-     postal_code,
latitude,
longitude,
acquisition_source,
registered_at,
registered_date_key (strftime %Y%m%d::integer)


*/
create or replace core.dim_customer as
select
    user_id,
    age,
    case 
        when age is null then 'Unknown',
        when age < 25 then '18-24'
        when age < 35 then '25-34'
        when age < 45 then '35-44'
        when age < 55 then '45-54'
        when age < 65 then '55-64'
        else '65+'
    end as age_band,
    gender,
    coalesce(country,'Unknown') as country,
    coalesce(state,'Unknown') as state,
    coalesce(city,'Unknown') as city,
    postal_code,
    latitude,
    longitude,
    acquisition_source,
    registered_at,
    cast(strftime(registered_at,%Y%m%d) as integer) as registered_date_key
    from stg.users


/* ============================================================
   5. SESSION TRAFFIC SOURCE DIMENSION (core.dim_session_traffic_source)
   Grain:
   One row per distinct session traffic source.

   This describes the source recorded during a website session.


create or replace table as
select row_number() over (
    order by traffic_source)
session_traffic_source_key, traffic_source
select distinct traffic_source from stg.sessions



   6. ACQUISITION SOURCE DIMENSION (core.dim_acquisition_source)

   Grain:
   One row per distinct customer acquisition source.

   This describes the source that originally acquired a user.

acquisition_source_key, acquisition_source



   ============================================================ */

create or replace table core.dim_session_traffic_source as
select 
    row_number() over (
    order by traffic_source) as session_traffic_source_key, 
    traffic_source
    from(
        select distinct traffic_source from stg.sessions
        )


create or replace table core.dim_acquisition_source as
select 
    row_number() over (
    order by acquisition_source) as acquisition_source_key, 
    acquisition_source
    from(
        select distinct acquisition_source from stg.users
        )










---File 01_staging.sql
/* ============================================================
   6. DERIVED SESSIONS

   This is not an original source table.

   Input grain:
       one row per event

   Output grain:
       one row per session_id



    create view as 

    from stg.events
    where session_id is not null
    group by session_id


column


-session_id

- user_id
choose one user 
max(user_id) as user_id

- event_count
count(*)::integer



- events_with_user_id
count(user_id)::integer

-event_identity_coverage_rate
cast the upper as double and nullif the below part

-session_start_at, session_end_at


Attributes attached to the earliest sequence number
city, state, postal_code, browser, traffic_source [arg_min(...,sequence_number) as ...]


first and final record event types
-first_event_type
-final_event_type [
                    arg_max(
                        event_type,
                        sequence_number) as final_event_type
                ]


funnel flags
- home_flag
- department_flag
- product_view_flag
- cart_flag
- purchase_flag
- cancel_event_flag
using max, case when 
    from stg.events
    where session_id is not null
    group by session_id
   ============================================================ */

select
session_id,
max(user_id) as user_id,
count(*)::integer as event_count,
count(user_id)::integer as events_with_user_id,
count(user_id)::double/nullif(count(*),0) as event_identity_coverage_rate,
min(created_at) as session_start_at,
max(created_at) as session_end_at,
arg_min(city, sequency_number) as city,
arg_min(state, sequence_number) as state,
arg_min(postal_code, sequence_number) as postal_code,
arg_min(browser, sequence_number) as browser,
arg_min(traffic_source, sequence_number) as traffic_source,
arg_min(event_type, sequence_number) as first_event_type,
arg_max(event_type, sequence_number) as final_event_type,
--funnel flags--
max(case when event_type = 'department' then 1 else 0 end) as department_flag,
max(case when event_type = 'home' then 1 else 0 end) as home_flag,
max(case when event_type = 'product' then 1 else 0 end) as product_view_flag,
max(case when event_type = 'cart' then 1 else 0 end) as cart_flag,
max(case when event_type = 'purchase' then 1 else 0 end) as purchase_flag,
max(case when event_type = 'cancel' then 1 else 0 end) as cancel_event_flag

from stg.events
where session_id is not null
group by session_id;



--File 03_core_facts.sql--

create schema if not exists core;

/* ============================================================
   1. ORDER FACT (core.fact_order)

   Grain:
   One row per order.
   create or replace table
   
   Column: order_id, customer_id, order_status, order_created_at, shipped_at, delivered_at, 
   returned_at, order_date_key, item_count, acquisition_source, ship_lead_days, 
   delivery_lead_days, end_to_end_lead_days, return_cycle_days, valid_timeline_flag, 
   cancelled_order_flag, returned_order_flag, completed_order_flag

   source: stg.orders

   First: 
   create schema if not exists core;


   before each table: create or replace table core. as
   select...
   

   current table alias: o

   --column needs building logic--
   ship_lead_days: time from created to shipped [using condition when shipped_at >= created_at
    datediff('minute', created_at, shipped_at)/ 1440.0]
   acquisition_source: join core.dim_customer
   order_date_key: use created_at
   delivery_lead_days: time from shipped to delivered
   end_to_end_lead_days: time from created to delivery 
   return_cycle_days: time from delivered to returned
   valid_timeline_flag: when things are wrong orders (this thing not null the related things are null
     or shipped_at  < created_at, delivered_at < shipped_at, returned_at < delivered-at, 
     (created_at is always not null) then 0, else 1 
   cancelled_order_flag: order_status = 'Cancelled', same for returned, completed, 
   ============================================================ */

create or replace table core.fact_order as
select
o.order_id,
o.user_id as customer_id,
o.order_status,
o.created_at as order_created_at,
o.shipped_at,
o.delivered_at,
o.returned_at,
cast(strftime(o.created_at, '%Y%m%d') as integer) as order_date_key,
o.item_count,
c.acquisition_source,
case when o.shipped_at >= o.created_at then datediff('minute', o.created_at, o.shipped_at)/1440.0 
         end as ship_lead_days,
case when o.deliverd_at >= o.shipped_at then datediff('minute', o.shipped_at, o.delivered_at)/1440.0 
         end as delivery_lead_days,
case when o.deliverd_at >= o.created_at then datediff('minute', o.created_at, o.delivered_at)/1440.0 
         end as end_to_end_lead_days,
case when o.returned_at >= o.delivered_at then datediff('minute', o.delivered_at, o.returned_at)/1440.0 
         end as return_cycle_days,
case when o.shipped_at is not null and o.shipped_at < o.created_at then 0
     when o.delivered_at is not null and o.shipped_at is null or o.delivered_at < o.shipped_at then 0
     when o.returned_at is not null and 0.delivered_at is null or o.returned_at < o.delivered_at then 0
     else 1 end as valid_timeline_flag,
case when o.order_status = 'Cancelled' then 1 else 0 end as cancelled_order_flag,
case when o.order_status = 'Returned' then 1 else 0 end as returned_order_flag,
case when o.order_status = 'Completed' then 1 else 0 end as completed_order_flag
from stg.orders o 
LEFT JOIN core.dim_customer c
    on o.user_id = c.user_id;









/* ============================================================
   2. ORDER-ITEM FACT (core.fact_order_item)

   Grain:
   One row per product line in an order.

   This is the primary financial fact because revenue, cost,
   profit, cancellation and return happen at item grain.

   Source: stg.order_items

   current table alias: i

   Column: order_item_id, order_id, customer_id, product_id, inventory_item_id, distribution_center_id, 
   aquisition_source, item_status, order_item_created_at, shipped_at, delivered_at, retunred_at, 
   order_date_key, sale_price, unit_cost, gross-margin_value, gross_margin_rate, cancelled_value,
   returned_value, net_profit_value, cancelled_item_flag, returned_item_flag, 
   return_observation_eligible_flag, ship_lead_days, delivery_lead_days, end_to_end_lead_days, 
   return_cycle_days, valid_timeline_flag

   --column needs building logic--
   order_date_key: using created at
   gross_margin_value: sale_price - unit_cost
   gross_margin_rate: when sale_price > 0 then (sale_price-unit_cost)/sale_price
   gross_sales_value: sale_rpice

   cancelled_value: when item_status = 'Cancelled' then sale_price else 0
   same for returned_value
   net_sales_value: status not in ('Cancelled', 'Returned') then sale_price else 0
   net_profit_value: status not in ('Cancelled', 'Returned') then sale_price-unit_cost else 0
   cancelled_item_flag: status = 'Cancelled'
   returned_item_flag: status = 'Returned'
   return_observation_eligible_flag: status in ('Complete', 'Returned') then 1 else 0

    left join core.dim_product (p)
    left join core.dim_customer (c) 
   ============================================================ */

select
    i.order_item_id,
    i.order_id,
    i.user_id as customer_id,
    i.product_id,
    i.inventory_item_id,
    p.distribution_center_id,
    c.acquisition_souce,
    i.item_status, 
    i.created_at as order_item_created_at, 
    i.shipped_at,
    i.delivered_at,
    i.returned_at, 
    cast(strftime(i.created_at, '%Y%m%d') as integer) as order_date_key,
    i.sale_price,
    p.unit_cost,
    i.sale_price - p.unit_cost as gross_margin_value,
    case when i.sale_price > 0 then (i.sale_price - p.unit_cost)/ i.sale_price end as gross_margin_rate,
    i.sale_price as gross_sales_value,
    case when i.item_status = 'Cancelled' then i.sale_price else 0 end as cancelled_value,
    case when i.item_status = 'Returned' then i.sale_price else 0 end as returned_value,
    case when i.item_status  not in ('Cancelled', 'Returned') then i.sale_price else 0 end as net_sales_value,
    case when i.item_status  not in ('Cancelled', 'Returned') then i.sale_price - p.unit_cost else 0 end as net_profit_value,
    case when i.item_status = 'Cancelled' then 1 else 0 end as cancelled_item_flag,
    case when i.item_status = 'Returned' then 1 else 0 end as returned_item_flag,
    case when i.item_status in ('Complete', 'Returned') then 1 else 0
    from stg.order_items i
    left join core.dim_product p
        on i.product_id = p.product_id
    left join core.dim_customer c
        on i.user_id = c.user_id 




/* ============================================================
   3. SESSION FACT (core.fact_session)

   Grain:
   One row per session_id.

   stg.sessions was derived from stg.events. It is not an
   original source table.
   Column: session_id, customer_id, session_start_at, session_end_at,  
   sesion_date_key, browser, traffic_source, country, event_count, events_with_user_id, 
   event_identity_coverage_rate, identified_session_flag, session_duration_seconds, 
   first_event_type, final_event_type, home_flag, department_flag, product_view_flag, cart_flag,
   purchase_flag, cart_abandoned_flag, early_product_exit_flag, highest_stage
   current table alias: s
   --column needs building logic--

   session_date_key: session_start_at
   country: join from c also using coalesce
   identified_session_flag: events_with_user_id > 0
   session_duration_seconds: when session_end_at >= session_start_at then datediff('second', session)
   cart_abandoned_flag: cart_flag = 1 and purchase_flag = 0 then 1 else 0
   early_product_exit_flag: when product_view_flag = 1 and cart_flag = 0 and purchase_flag = 0
   highest_stage: purchase_flag = 1 then 'Purchase', when cart_flag = 1 then 'Product' when department_flag = 1 then 'Department'
   else 'Home'


   join core.dim_customer (c)

   ============================================================ */

select
s.sesison_id,
s.user_id as customer_id,
s.sesstion_start_at,
s.session_end_at,
cast(strftime(session_start_at, '%Y%m%d') as integer) as session_date_key,
s.browser, 
s.traffic_source,
coalesce(c.country,'Unknown') as country,
s.event_count,
s.events_with_user_id,
s.events_identity_coverage_rate,
case when s.events_with_user_id > 0 then 1 else 0 end as identified_session_flag,
case when s.session_end_at >= s.session_start_at then datediff('second', s.session_start_at, s.session_end_at) as session_duration_seconds,
s.first_event_type,
s.final_event_type,
s.home_flag,
s.department_flag,
s.product_view_flag,
s.cart_flag,
s.purchase_flag,
s.cancel_event_flag,
case when s.cart_flag = 1 and s.purchase_flag = 0 then 1 else 0 end as cart_abandoned_flag,
case when s.product_view_flag = 1 and s.cart_flag = 0 and s.purchase_flag = 0 then 1 else 0 end as early_product_exit_flag,
case when s.purchase_flag = 1 then 'Purchase'
     when s.cart_flag = 1 then 'Cart'
     when s.product_view_flag = 1 then 'Product'
     when s.department_flag = 1 then 'Department'
     else 'Home'
     end as highest_stage
     
from stg.sessions s
left join core.dim_customer c
    on s.user_id = c.user_id;





/* ============================================================
   4. INVENTORY FACT (core.fact_inventory)

   Grain:
   One row per physical inventory item.

   The as-of date comes from the dataset, not today's date.
   This keeps the output reproducible.
   column: inventory_item_id; product_id, inventory_created_at; sold_at; inventory_created_date_key; 
   unit_cost, retail_price, sold_flag, days_to_sell, unsold_age_days, inventory_age_bucket

   current table alias: i
    with as_of as (
    select max(created_at)::DATE as as_of_date from stg.events)
    --column needs building logic--
    inventory_created_date_key: using created_at
    sold_flag: sold_at is not null
    days_to-sell: when sold_at >= created_at then datediff('days', created_at, sold_at)
    unsold_age_days: sold_at is null then datediff('days', created_at::DATE, as_of.as_of_date)
    inventory_age_bucket:
       when sold_at is not null then 'Sold'
       when datediff('day', created_at, as_of.as_of_date) <=30 then '0-30 days'
       when...<= 60 then '31-60 days'
       when...<= 90 then '61-90 days'
       when...<= 180 then '91-180 days'
       else '181+ days'
    
   cross join as_of 

   ============================================================ */


with as_of as(
    select max(created_at)::DATE as as_of_date
    from stg.events
)
select
    i.inventory_item_id,
    i.product_id,
    i.created_at as inventory_created_at,
    i.sold_at,
    cast(strftime(i.created_at,'%Y%m%d') as integer) as inventory_created_date_key,
    i.unit_cost,
    i.retail_price,
    case when i.sold_at is not null then 1 else 0 end as sold_flag,
    case when i.sold_at >= i.created_at then datediff('days', i.created_at, i.sold_at) end as days_to_sell,
    case when i.sold_at is null then datediff('days', i.created_at::DATE, as_of.as_of_date) end as unsold_age_days,
    case when i.sold_at is not null then 'Sold'
         when datediff('day', i.created_at::DATE, as_of.as_of_date) <= 30 then '0-30 days'
         when datediff('day', i.created_at::DATE, as_of.as_of_date) <= 60 then '31-60 days'
         when datediff('day', i.created_at::DATE, as_of.as_of_date) <= 90 then '61-90 days'
         when datediff('day', i.created_at::DATE, as_of.as_of_date) <= 180 then '91-180 days'
         else '180+ days'
         end as inventory_age_bucket,
    from stg.inventory_events i
    cross join as_of;




--File 04_mart_acquisition_funnel.sql
/* ============================================================
   04_mart_acquisition_funnel.sql

   Purpose:
   Create acquisition, channel, funnel and abandonment marts.

   Inputs:
   - core.fact_session
   - core.fact_order_item

   Outputs:
   - mart.funnel_stage_channel
   - mart.funnel_monthly_channel
   - mart.cart_abandonment_segments
   - mart.channel_quality
   - mart.acquisition_source_value
   ============================================================ */

create schema if not exists;

/* ============================================================
   1. FUNNEL STAGE BY CHANNEL (mart.funnel_stage_channel)

   Grain:
   One row per traffic source and funnel stage.


   source:core.fact_session
   columns:
 traffic_source, stage_order, stage, stage_sessions, conversion_from_session_rate, 
 conversion_from_previous_stage_rate

union all these in vertical
cte stage_counts
from core.fact_session, group by traffic source
traffic_source: 
 1,2,3,4 as stage_order,
 'Name' as stage (Session, Product Viewed, Cart Reached, Purchase),
 aggregate(count(*) or sum) as stage_sessions
union
cte windowed
from stage_counts
select *,
--add more 2 columns

first_value(stage_sessions) over (partition by traffic_source order by stage_order) 
as initial_sessions,
lag(stage_sessions) over (partition by traffic_source order by stage_order) as previous_stage_sessions
main query:
from windowed

select traffic_source, stage_order, stage, stage_sessions,
 conversion_from_session_rate: stage_sessions (::double)/ nullif(initial_sessions, 0)
 conversion_from_previous_stage_rate: stage_sessions (::double)/ nullif(previous_stage_sessions, 0)

   ============================================================ */

create or replace table mart.funnel_stage_channel as
with stage_counts as (
    select traffic_source,
           1 as stage_order,
           'Session' as stage,
           count(*) as stage_sessions
    from core.fact_session
    group by traffic_source

    union all

    select traffic_source,
           2 as stage_order,
           'Product Viewed' as stage,
           sum(product_view_flag) as stage_sessions
    from core.fact_session
    group by traffic_source

    union all

    select traffic_source,
           3 as stage_order,
           'Cart Reached' as stage,
           sum(cart_flag) as stage_sessions
    from core.fact_session
    group by traffic_source

    union all

    select traffic_source,
  
           4 as stage_order,
           'Purchase' as stage,
           sum(purchase_flag) as stage_sessions
    from core.fact_session
    group by traffic_source

),
windowed as (
    select
        *,
        first_value(stage_sessions) over (partition by traffic_source order by stage_order) as initial_sessions,
        lag(stage_sessions) over (partition by traffic_source order by stage_order) as previous_stage_sessions
    from stage_counts
)
select
    traffic_source,
    stage_order,
    stage,  
    stage_sessions,
    stage_sessions::double/nullif(initial_sessions,0) as conversion_from_session_rate,
    stage_session::double/nullif(previous_stage_sessions,0) as conversion_from_previous_stage_rate
from windowed;

/* ============================================================
   2. MONTHLY FUNNEL BY CHANNEL (mart.funnel_monthly_channel)

   Grain:
   One row per month and traffic source.

   Source: core.fact_session
   Column: month_start, traffic_source, sessions, users, product_view_sessions, cart_sessions, 
   purchase_sessions, abandoned_cart_sessions, session_conversion_rate, cart_abandonment_rate, 
   avg_events_per_session, avg_session_duration_seconds, avg_event_identity_coverage_rate

   group_by month_start (date_trunc('month', session_start_at))
            traffic_source
   ============================================================ */
   create or replace table mart.funnel_monthly_channel as
   select
        date_trunc('month',session_start_at):date as month_start,
        traffic_source,
        count(*) as sessions,
        count(distinct customer_id) as users,
        sum(product_view_flag) as product_view_sessions,
        sum(cart_flag) as cart_sessions,
        sum(purchase_flag) as purchase_sessions, 
        sum(cart_abandoned_flag) as abandoned_cart_sessions,
        sum(purchase_flag)::double/ nullif(count(*), 0) as session_conversion_rate,
        sum(cart_abandoned_flag)::double / nullif(sum(cart_flag),0) as cart_abandonment_rate,
        avg(event_count) as avg_events_per_session,
        avg(session_duration_seconds) as avg_session_duration_seconds,
        avg(event_identity_coverage_rate) as avg_event_identity_coverage_rate

    from core.fact_session
    group by month_start, traffic_source;



/* ============================================================
   3. CART ABANDONMENT SEGMENTS (mart.cart_abandonment_segments)

   Grain:
   One row per segment type and segment value.

   Minimum sample:
   At least 500 sessions.

   Columns: segment_type, segment_vale, sessions, cart_sessions, abandoned_cart_sessions, purchase_sessions, 
   cart_abandonment_rate, session_conversion_rate


   first table: segments
   Column: segment_type, segment_value, sessions, cart_sessions, abandoned_cart_sessions, purchase_sessions
   Method: use traffic_source, browser, country, group by each, from core.fact_session

   2nd table - main
   all from 1st table, 
   cart_abandonment_rate,
   session_conversion_rate

   filter session >=500;
   ============================================================ */

create or replace table mart.cart_abandonment_segments as

with segments as(
    select
        'Traffic Source' as segment_type,
        traffic_source as segment_value,
        count(*) as sessions,
        sum(cart_flag) as cart_session,
        sum(cart_abandoned_flag) as abandoned_cart_sessions,
        sum(purchase_flag) as purchase_sessions
    from core.fact_session
    group by traffic_source

    union all

    select
        'Browser' as segment_type,
        browser as segment_value,
        count(*) as sessions,
        sum(cart_flag) as cart_sessions,
        sum(cart_abandoned_flag) as abandoned_cart_sessions,
        sum(purchase_flag) as purchase_sessions
    from core.fact_session
    group by browser

    union all
    
    select
        'Country' as segment_type,
        country as segment_value,
        count(*) as sessions,
        sum(cart_flag) as cart_session,
        sum(cart_abandoned_flag) as abandoned_cart_sessions,
        sum(purchase_flag) as purchase_sessions
    from core.fact_session
    group by country
)
select 
    *,
    abandoned_cart_sessions::double/ nullif(cart_sessions, 0) as cart_abandonment_rate,
    purchase_sessions::double/nullif(sessions,0) as session_conversion_rate
from segments
where sessions >=500;



/* ============================================================
   4. CHANNEL QUALITY (mart.channel_quality)

   Grain:
   One row per session traffic source.
   Column: traffic_source, sessions, users, cart-sessions, purchase_sessions, abandoned_cart_sessions, 
   avg_events_per_session, avg_event_identity_coverage_rate, session_conversion_rate, cart_abandonment_rate
   
   from core.fact_session 
   group by traffic source


   ============================================================ */

select
    traffic_source,
    count(*) as sessions,
    count( distinct customer_id) as users,
    sum(cart_flag) as cart_sessions,
    sum(purchase_flag) as purchase_sessions,
    sum(cart_abandoned_flag) as abandoned_cart_sessions,
    avg(event_count) as avg_event_per_session,
    avg(event_identity_coverage_rate) as avg_event_identity_coverage_rate,
    sum(purchase_flag)::double/nullif(count(*),0) as session_conversion_rate,
    sum(cart_abandoned_flag)::double/nullif(sum(cart_flag),0) as cart_abandonment_rate
    
from core.fact_session
group by traffic_source;
 

/* ============================================================
   5. ACQUISITION-SOURCE VALUE (mart.acquisition_source_value)

   Grain:
   One row per customer acquisition source.

   Note:
   Acquisition source describes how the customer was originally
   acquired. It is different from session traffic source.

   Column: acquisition_source, orders, customers, gross_sales_value, net_sales_value, net_profit_value,
   net_sales_per_customer


   customers: count( distinct customer_id)
   orders: count(distinct order_id)
   group by acquisition_source
   from: core.fact_order_item
   ============================================================ */


select
    acquisition_source,
    count(distinct order_id) as orders,
    count(distinct customer_id) as customers,
    sum(gross_sales_value) as gross_sales_value,
    sum(net_sales_value) as net_sales_value,
    sum(net_profit_value) as net_profit_value,
    sum(net_sales_value)::double/nullif(count(distinct customer_id),0) as net_sales_per_customer
    from core.fact_order_item
    group by acquisition_source;



/* ============================================================
   File 05_mart_commercial_customer.sql

   Purpose:
   Create sales, product, geography, customer and cohort marts.

   Outputs:
   - mart.sales_monthly
   - mart.product_performance_category
   - mart.product_performance_brand
   - mart.geography_performance_country
   - mart.customer_360
   - mart.cohort_retention
   ============================================================ */




/* ============================================================
   1. MONTHLY SALES 
   mart.sales_monthly

   Grain:
   One row per month.
   Source: core.fact_order_item (f)
   Join: inner join core.dim_date (d) on date_key
   Group by: month_start, year, month_number
   Column: month_start, year, month_number, is_complete_month, orders, customers, items, gross_sales_value, 
    cancelled_value, returned_value, net_sales_value, net_profit_value, net_margin_rate, average_order_value, 
    items_per_order, items_cancellation_rate, item_return_rate


   ============================================================ */

create or replace table mart.sales_monthly as
select
    d.month_start,
    d.year,
    d.month_number
    max(d.is_complete_month) as is complete_month,
    count(distinct f.order_id) as orders,
    count(distinct f.customer_id) as customers,
    count(*) as items,
    sum(f.gross_sales_value) as gross_sales_value,
    sum(f.cancelled_value) as cancelled_value,
    sum(f.returned_value) as returned_value,
    sum(f.net_sales_value) as net_sales_value,
    sum(f.net_profit_value) as net_profit_value,
    sum(f.net_profit_value)::double/nullif(sum(f.net_sales_value),0) as net_margin_rate,
    sum(f.net_sales_value)/nullif(count(distinct f.order_id),0) as average_order_value,
    count(distinct f.order_item_id)/nullif(count(distinct f.order_id),0) as items_per_order,
    sum(f.cancelled_item_flag)/nullif(count(distinct f.order_item_id),0) as item_cancellation_rate,
    sum(f.returned_item_flag)/nullif(count(distinct f.order_item_id),0) as item_return_rate
    from core.fact_order_item f
    inner join core.dim_date d
        on f.order_date_key = d.date_key
    group by month_start, year, month_number;
/* ============================================================
   2. CATEGORY PERFORMANCE
   mart.product_performance_category

   Grain:
   One row per department and category.

   Source: core.fact_order_item (f)
   Join: inner join core.dim_product (p) on product_id
   Group by: department, category

   Column: department, category, products, orders, customers, items, gross_sales_value, net_sales_value, net_profit_value,
    net_margin_rate, returned_items, observed_return_rate, cancellation_rate


   ============================================================ */

create or replace table mart.product_performance_category as
select
    p.department,
    p.category,

    count(distinct f.order_id) as orders,
    count(distinct f.customer_id) as customers,
    count(distinct f.product_id) as products,
    count(*) as items,
    sum(f.gross_sales_value) as gross_sales_value,
    sum(f.net_sales_value) as net_sales_value,
    sum(f.net_profit_value) as net_profit_value,
    sum(f.net_profit_value)::double/nullif(sum(f.net_sales_value),0) as net_margin_rate,
    sum(f.returned_item_flag) as returned_items,
    sum(f.return_observation_eligible_flag) as return_observation_eligible_items,
    sum(f.returned_item_flag)::double/nullif(sum(f.return_observation_eligible_flag),0) as observed_return_rate,
    sum(f.cancelled_item_flag)::double/nullif(count(*),0) as cancellation_rate
    from core.fact_order_item f
    inner join core.dim_product p
        on f.product_id = p.product_id
    group by p.department, p.category;  




/* ============================================================
   3. BRAND PERFORMANCE
   mart.product_performance_brand

   Grain:
   One row per brand.

   Source: core.fact_order_item (f)
   Join: inner join core.dim_product (p) on product_id
   Group: brand

   Column: brand, categories, products, orders, items, net_sales_value, net_profit_value, net_margin_rate, 
    observed_return_rate

   ============================================================ */

create or replace table mart.product_performance_brand as
select
    p.brand,
    count(distinct p.category) as categories,
    count(distinct p.product_id) as products,
    count(distinct f.order_id) as orders,
    count(distinct f.order_item_id) as items,
    sum(f.net_sales_value) as net_sales_value,
    sum(f.net_profit_value) as net_profit_value,
    sum(f.net_profit_value)::double/nullif(sum(f.net_sales_value),0) as net_margin_rate,
    sum(f.return_observation_eligible_flag) as return_observation_eligible_items,
    sum(f.returned_item_flag)::double/nullif(sum(f.return_observation_eligible_flag),0) as observed_return_rate
    from core.fact_order_item f
    inner join core.dim_product p
        on f.product_id = p.product_id
    group by brand;



/* ============================================================
   4. COUNTRY PERFORMANCE
   Name: mart.geography_performance_country

   Grain:
   One row per customer country.

   Source: core.fact_order_item (f)
   Join: inner join core.dim_customer (c) on f.customer_id = c.user_id
   Group by: country

   Column: country, orders, customers, items, net_sales_value, net_profit_value, average_order_value, 
    observed_return_rate
   ============================================================ */
create or replace table mart.geography_performance_country as
select
    c.country,
    count(distinct f.order_id) as orders,
    count(distinct f.customer_id) as customers,
    count(*) as items,
    sum(f.net_sales_value) as net_sales_value,
    sum(f.net_profit_value) as net_profit_value,
    sum(f.net_sales_value)/nullif(count(distinct f.order_id),0) as average_order_value,
    sum(f.return_observation_eligible_flag) as return_observation_eligible_items,
    sum(f.returned_item_flag)::double/nullif(sum(f.return_observation_eligible_flag),0) as observed_return_rate
from core.fact_order_item f
inner join core.dim_customer c
    on f.customer_id = c.user_id
group by c.country;






/* ============================================================
   5. CUSTOMER 360
   mart.customer_360
   Grain:
   One row per purchasing customer.
   This includes only customers with at least one order item.
   Source and join: 
    1. as_off from core.fact_order_item
        source: core.fact_order_item
        column: as_of_date [max(order_item_created_at)::date]
    2. customer_sales from core.fact_order_item group by customer_id
        source: core.fact_order_item
        column: customer_id, first_order_date, last_order_date, order_count, item_count, gross_sales_value, 
            net_sales_value, net_profit_value, returned_items, cancelled_items, return_eligible_items 
            Break down:
                first_order_date: min(order_item_created_at)::date
                last_order_date: max...

    3. main table
        source: core.dim_customer (c) inner join customer_sales (s) on c.user_id = s.customer_id; cross join as_off
        column: customer_id, age, age_brand, gender, country, state, city, acquisition_source, registered_at, 
            first_order_date, first_order_cohort_month, recency_days, order_count, item_count, gross_sales_value, net_sales_value,
            net_profit_value, average_order_value, returned_items, cancelled_items, observed_return_rate, 
            repeat_customer_flag

            Break down: 
                first_order_cohort_month: date_trunc('month', first_order_date)::date
                recency_days: datediff('day', last_order_date, as_of.as_of_date)
                repeat_customer_flag: case when order_count >=2
   ============================================================ */

create or replace table as mart.customer_360 as
with as_of as(
    select
        max(order_item_created_at)::date as as_of_date
    from core.fact_order_item
),
customer_sales as (
    select
        customer_id,
        min(order_item_created_at)::date as first_order_date,
        max(order_item_created_at)::date as last_order_date,
        count(distinct order_id) as order_count,
        count(*) as item_count,
        sum(gross_sales_value) as gross_sales_value,
        sum(net_sales_value) as net_sales_value,
        sum(net_profit_value) as net_profit_value,
        sum(returned_item_flag) as returned_items,
        sum(cancelled_item_flag) as cancelled_items,
        sum(return_observation_eligible_flag) as return_eligible_items
    from core.fact_order_item
    group by customer_id
    )
    select
        c.user_id as customer_id,
        c.age, c.age_band, c.gender, c.country, c.state, c.city, c.acquisition_source, c.registered_at,
        s.first_order_date, s.last_order_date, 
        date_trunc('month', s.first_order_date)::date as first_order_cohort_month,
        datediff('day',s.last_order_date, a.as_of_date) as recency_days,
        s.order_count, s.item_count, s.gross_sales_value, s.net_sales_value, s.net_profit_value,
        s.net_sales_value::double/nullif(s.order_count,0) as average_order_value, s.returned_items, 
        s.cancelled_items, s.returned_items::double/nullif(s.return_eligible_items,0) as observed_return_rate,
        case when s.order_count >= 2 then 1 else 0 end as repeat_customer_flag
        
    from core.dim_customer c
    inner join customer_sales s
        on c.user_id = s.customer_id
    cross join as_of a






        
        
        
        
        






/* ============================================================
   6. COHORT RETENTION
   mart.cohort_retention

   Grain:
   One row per cohort month and months since first order.

   Activity includes a customer once per active month.

   Tables
    1. eligible_activity: 
        source: core.fact_order_item
        condition: net_sales_value > 0 
        column: customer_id, activity_month
            - activity_month: date_trunc('month', order_item_created_at)::date as activity_month
    2. cohorted:
        source: eligible_activity
        condition:
        column: customer_id, cohort_month, activity_month
            - cohort_month: min(activity_month) over (partition by customer_id) as cohort_month
    3. cohort_sizes: 
        source: cohorted
        group_by: cohort_month
        column: cohort_month, cohort_size (count(distinct customer_id))
    4. main table
        source: cohorted c, inner join cohort_sizes s using (cohort_month)
        group by: cohort_month, months_since_first_order, cohort_size
        column: cohort_month, months_since_first_order, cohort_size, active_customers, retention_rate
        Break down:
            - months_since_first_order: datediff('month',cohort_month, activity_month)
            - active_customers: count(distinct customer_id)
            - retention_rate: count(distinct customer_id)/nullif(cohort_size, 0)

 
   Column: cohort_month, months_since_first_order, cohort_size, active_customers, retention_rate
   ============================================================ */
create or replace table mart.cohort_retention as
with eligible_activity as(
    select 
        customer_id,
        date_trunc('month',order_item_created_at)::date as activity_month
    from core.fact_order_item
    where net_sales_value > 0

),
cohorted as (
    select
        customer_id,
        min(activity_month) over (partition by customer_id) as cohort_month,
        activity_month
    from eligible_activity
),
cohort_sizes as (
    select
        cohort_month,
        count(distinct customer_id) as cohort_size
    from cohorted
    group by cohort_month
)
select
    c.cohort_month,
    datediff('month',c.cohort_month, c.activity_month) as months_since_first_order,
    s.cohort_size,
    count(distinct c.customer_id) as active_customers,
    count(distinct c.customer_id)/nullif(s.cohort_size, 0) as retention_rate
from cohorted c
inner join cohort_sizes s
    using (cohort_month)
group by c.cohort_month, months_since_first_order, s.cohort_size;

    



/* ============================================================
   File 06_mart_operations_inventory.sql

   Purpose:
   Create operations, delivery, return-risk and inventory marts.

   Outputs:
   - mart.operations_monthly
   - mart.delivery_performance_dc
   - mart.return_risk_segments
   - mart.inventory_performance
   ============================================================ */



/* ============================================================
   1. MONTHLY OPERATIONS
   mart.operations_monthly

   Grain:
   One row per month.

   source: core.fact_order_item f join dim_date s to take month_start

   column: month_start, items, valid_timeline_items, avg_ship_lead_days, median_ship_lead_days, 
   p90_ship_lead_days, avg_delivery_lead_days, median_delivery_lead_days, p90_delivery_lead_days,
   avg_end_to_end_lead_days, p90_end_to_end_lead_days, observed_return_rate, cancellation_rate

 
   ============================================================ */

create or replace table mart.operations_monthly as
select
    d.month_start,
    count(*) as items,
    sum(f.valid_timeline_flag) as valid_timeline_items,
    avg(f.ship_lead_days) as avg_ship_lead_days,
    median(f.ship_lead_days) as median_ship_lead_days,
    quantile_cont(f.ship_lead_days, 0.90) as p90_ship_lead_days,
    avg(f.delivery_lead_days) as avg_delivery_lead_days,
    median(f.delivery_lead_days) as median_delivery_lead_days,
    quantile_cont(f.delivery_lead_days, 0.90) as p90_delivery_lead_days,
    avg(f.end_to_end_lead_days) as avg_end_to_end_lead_days,
    MEDIAN(f.end_to_end_lead_days) AS median_end_to_end_lead_days,
    quantile_cont(f.end_to_end_lead_days, 0.90) as p90_end_to_end_lead_days,
    sum(f.returned_item_flag)::double/nullif(sum(f.return_observation_eligible_flag),0) as observed_return_rate,
    sum(f.cancelled_item_flag)::double/nullif(count(*),0) as cancellation_rate
from core.fact_order_item f
inner join core.dim_date d
    on f.order_date_key = d.date_key;
group by d.month_start






/* ============================================================
   2. DELIVERY PERFORMANCE BY DISTRIBUTION CENTER
   mart.delivery_performance_dc

   Grain:
   One row per distribution center.

   column: distribution_center_id, distribution_center_name, items, valid_timeline_items, avg_ship_lead_days, 
   median_ship_lead_days, p90_ship_lead_days, avg_delivery_lead_days, median_delivery_lead_days, 
   p90_delivery_lead_days, avg_end_to_end_lead_days, p90_end_to_end_lead_days, observed_return_rate
   ============================================================ */
create or replace table mart.delivery_performancer_dc as
select
    dc.distribution_center_id,
    dc.distribution_center_name,
    count(*) as items,
    sum(f.valid_timeline_flag) as valid_timeline_items,
    avg(f.ship_lead_days) as avg_ship_lead_days,
    median(f.ship_lead_days) as median_ship_lead_days,
    quantile_cont(f.ship_lead_days, 0.90) as p90_ship_lead_days,
    avg(f.delivery_lead_days) as avg_delivery_lead_days,
    median(f.delivery_lead_days) as median_delivery_lead_days,
    quantile_cont(f.delivery_lead_days, 0.90) as p90_delivery_lead_days,
    avg(f.end_to_end_lead_days) as avg_end_to_end_lead_days,
    MEDIAN(f.end_to_end_lead_days) AS median_end_to_end_lead_days,
    quantile_cont(f.end_to_end_lead_days, 0.90) as p90_end_to_end_lead_days,
    sum(f.returned_item_flag)::double/nullif(sum(f.return_observation_eligible_flag),0) as observed_return_rate
from core.fact_order_item f
inner join core.dim_distribution_center dc
    on f.distribution_center_id = dc.distribution_center_id
group by distribution_center_id, distribution_center_name;

/* ============================================================
   3. RETURN-RISK SEGMENTS
   mart.return_risk_segments

   Grain:
   One row per segment type and segment value.

   Minimum sample:
   At least 100 eligible return observations.

   1. segments
   source: core.fact_order_item (f) 
  
   column: segment_type, segment_value, items, eligible items, returned items, returned value
   union all On category (join dim_product p), country (join dim customer c), age_band (join dim customer c), acquisition_source (no join), 
   also group by these

   2. main table
   columns: segment_type, segment_value, items, eligible_items, returned_items, returned_value, observed_return_rate
   condition: eligible_items >= 100;    

   ============================================================ */

create or replace table mart.return_risk_segments as
with segments as (
    select
        'Category' as segment_type,
        p.category as segment_value,
        count(distinct f.order_item_id) as items, 
        sum(f.return_observation_eligible_flag) as eligible_items,
        sum(f.returned_item_flag) as returned_items,
        sum(f.returned_value) as returned_value
    from core.fact_order_item f
    inner join core.dim_product p
        on f.product_id = p.product_id
    group by p.category

    union all

    select
        'Country' as segment_type,
        c.country as segment_value,
        count(distinct f.order_item_id) as items, 
        sum(f.return_observation_eligible_flag) as eligible_items,
        sum(f.returned_item_flag) as returned_items,
        sum(f.returned_value) as returned_value
    from core.fact_order_item f
    inner join core.dim_customer c
        on f.customer_id = c.user_id
    group by c.country

    union all

        'Age Band' as segment_type,
        c.age_band as segment_value,
        count(distinct f.order_item_id) as items, 
        sum(f.return_observation_eligible_flag) as eligible_items,
        sum(f.returned_item_flag) as returned_items,
        sum(f.returned_value) as returned_value
    from core.fact_order_item f
    inner join core.dim_customer c
        on f.customer_id = c.user_id
    group by c.age_band

    union all

        'Acquisition Source' as segment_type,
        acquisition_source as segment_value,
        count(distinct order_item_id) as items, 
        sum(return_observation_eligible_flag) as eligible_items,
        sum(returned_item_flag) as returned_items,
        sum(returned_value) as returned_value
    from core.fact_order_item
    group by acquisition_source
)
select 
    segment_type, segment_value, items, eligible_items, returned_items, returned_value,
    returned_items::double/nullif(eligible_items,0) as observed_return_rate
from segments
where eligible_items >= 100;







/* ============================================================
   4. INVENTORY PERFORMANCE
   mart.inventory_performance

   Grain:
   One row per department, category and distribution center.

   Source: core.fact_inventory i join dim_product p on product_id, join distribution center dc on distribution_center_id
   Group by: department, category, distribution_center_name
   Column: department, category, distribution_center_name, inventory_units, sold_units, unsold_units, 
   sell_through_rate, median_days_to_sell, p90_days_to_sell, aged_181_plus_units, unsold_inventory_cost, unsold_inventory_retail_value
   ============================================================ */

   create or replace table mart.inventory_performance as
   select
        p.department,
        p.category,
        dc.distribution_center_name,
        count(*) as inventory_units,
        sum(i.sold_flag) as sold_units,
        count(*) - sum(i.sold_flag) as unsold_units,
        sum(i.sold_flag)::double/nullif(count(*),0) as sell_through_rate,
        median(i.days_to_sell) as median_days_to_sell,
        quantile_cont(i.days_to_sell, 0.90) as p90_days_to_sell,
        sum(case when i.sold_flag = 0 and i.nventory_age_bucket = '181+ days' then 1 else 0 end) as aged_181_plus_units,
        sum(case when i.sold_flag = 0 then i.unit_cost end) as unsold_inventory_cost,
        sum(case when i.sold_flag = 0 then i.retail_price	end) as unsold_inventory_retail_value
    from core.fact_inventory i
    inner join core.dim_product p
        on i.product_id = p.product_id
    inner join core.dim_distribution_center dc
        on i.distribution_center_id= dc.distribution_center_id
    group by 
        p.department,
        p.category,
        dc.distribution_center_name;



--07_quality_and_snapshots.sql
/* ============================================================
   1. QA TEST RESULTS
   Common output:
   - check_name
   - layer: core, staging
   - severity: HIGH, INFO, CRITICAL, WARNING
   - status:WARN, INFO, PASS, FAIL
   - blocking: 0, 1
   - failure_count: 
   - denominator
   - failure_pct
   - handling_rule
   
   Prinary key uniqueness
    
============================================================ */   
   
   
    with checks as (
    'dim_customer_key_unique' 
        core
        CRITICAL
        failure_count: count(*) - count(distinct user_id)
        denominator: count(*)
        1
        'Every customer must have one unique user_id'
        --core.dim_customer--
    
    dim_product_key_unique
        core
        CRITICAL
        failure_count: count(*) - count(distinct product_id)
        denominator
        1
        Every product must have one unique product_id
        --core.dim_product--

    'dim_date_key_unique'
        core
        CRITICAL
        failure_count: date_key
        1,
        'Every calendar date must have one unique date key'
        --core.dim_date--

    'dim_distribution_center_key_unique'
        core
        CRITICAL
        failure_stage: distribution_center_id
        denominator
        1
        'Every distribution center must have one unique ID'
        --core.dim_distribution_center--
    
    'fact_order_key_unique'
        core
        CRITICAL
        failure_count:order_item_id
        denominator
        1
        'Every order item must appear once in fact_order_item'
        --core.fact_order_item--

    'fact_inventory_key_unique'
        core
        CRITICAL
        failure_count: inventory_item_id
        denominator
        1
        'Every inventory item must appear once in fact_inventory'
        --core.fact_inventory--

    'fact_session_key_unique'
        core
        CRITICAL
        failure_count: session_id
        denominator
        1
        'Every session_id must produce exactly one fact-session row'
        --core.fact_session

    Session reconciliation
    'sesion_count_reconciles'
        core
        CRITICAL
        failure_count: abs(count distinct session id from stg.events where
            session_id is not null - count (*) from core.fact_session)
        denominator: select count(distinct session_id) from stg.events
            where session_id is not null
        1
        'Every distinct nonblank event session must produce one fact session'
    
    'session_event_count_reconciles'
        core
        CRITICAL
        failure_count: abs((select count(*) from stg.events where session_id is not null)-(select coalesce(sum(event_count),0)::bigint from core.fact_session))
        denominator
        1
        'Summed fact-session event counts must equal sessionizale events'



    'blank_event_session_ids'
        staging
        WARNING
        falure_count: count(*)
        denominator: select count(*) from stg.events
        0
        'Events without session_id are excluded from session analysis'
        --stg.events--where session_id is null
    
    'sessions_with_multiple_user_ids'
        staging
        HIGH
        failure_count: count(*) 
            Source: from (select session_id from stg.events
            where session_id is not null group by session_id having count(distinct user_id) > 1) as inconsistent_sessions
        denominator: select count(distinct session_id from stg.events where session_id is not null)
        1
        'One session should not be assigned to multiple users'

    Referential integrity

    'orders_without_customer'
    core
    HIGH
    count(*) as failure_count
        source: core.fact_oder f left join core.dim_customer c on f.customer_id = c.user_id where f.customer_id is not null and c.user_id is null
    denominator: select count(*) from core.fact_order
    'Every identified order must match a customer dimension row'

    'order_items_without_product'
    core
    CRITICAL
    failure_count: count(*)
        source: from core.fact_order_item i left join core.fact_order o on i.order_id = o.order_id where o.order_id is null
    denominator: select count(*) from core.fact_order_item
    1
    Every order item must match a producr

    inventory_without_product
    core
    HIGH
    failure_count: count(*)
        source: core.fact_inventory i left join core.dim_product p on i.product_id = p.product_id where p.product_is is null
    denominator: select count (*) from core.fact_inventory
    'Every inventory unit must match a product'
    1


    'inventory_without_distribution_center'
    core
    HIGH
    failure_count: count(*)
        source: core.fact_inventory i left join core.dim_distribution_center dc on i.distribution_center_id = dc.distribution_center_id where dc.distribution_center_id is null
    denominator: select count (*) from core.fact_inventory
    1
    'Every inventory unit must match a product'

    Commercial and timeline check

    'negatives_item_prices_or_costs'
    core
    HIGH
    failure_count: count(*)
        source: core.fact_order_item where sale_prices < 0 or unit_cost < 0
    denominator: select count(*) from core.fact_order_item)
    0
    'Review potentially loss-making items; do not silently remove them'

    'cost_above_sale_price'
    core
    WARNING
    failure_count: count(*)
        source: core.fact_order_item where unit_cost > sale_price
    denominator: selet count(*) from core.fact_order_item as denominator
    0
    'Review potentially loss-making items; do not silently remove them'

    'invalid_order_item_timeline'
    core
    HIGH
    failure_count: count(*)
        source: core.fact_order_item where valid_timeline_flag = 0
    denominator: select count(*) from core.fact_order_item
    0
    'Exclude invalid timelines from lead-time metrics and investigate them'


    Informational observations

    'events_without_user_id'
    staging
    INFO
    failure_count: count(*)
        source: stg.events where user_id is null
    denominator: select count (*) from stg.events
    0
    'Anonymous events remain valid for traffic analysis but not customer analysis'


    'rows_in_incomplete_maximum_month'
    core
    INFO
    failure_count: count(*)
        source: core.dim_date where is_complete_month = 0 and month_start = (select max(month_start) from core.dim_date))
    )

    select
        check_name,
        layer,
        severity,
        failure_count,
        denominator,
        blocking,
        handling_rule, 
        case when failure_count = 0 then 'PASS'
        when severity = 'INFO' then 'INFO'
        when blocking = 1 then 'FAIL'
        else 'WARN'
        end as status,

        failure_count::double / nullif(denominator,0) as failure_rate

        from checks;





    












    


























































