#!/bin/bash

# Qutebrowser userscript: report the first battery exposed by Linux sysfs.
# It accepts no input and emits only a fixed message-info command to QUTE_FIFO.

if [[ -z "${QUTE_FIFO:-}" || ! -p "${QUTE_FIFO}" || ! -w "${QUTE_FIFO}" ]]; then
    exit 0
fi

read_sysfs_value() {
    local path="$1"

    [[ -r "${path}" ]] || return 1
    IFS= read -r REPLY < "${path}" || return 1
    [[ -n "${REPLY}" ]]
}

unsigned_value() {
    local value="$1"

    [[ "${value}" =~ ^[0-9]+$ ]] || return 1
    printf '%d' "$((10#${value}))"
}

absolute_value() {
    local value="$1"

    [[ "${value}" =~ ^-?[0-9]+$ ]] || return 1
    value="${value#-}"
    printf '%d' "$((10#${value}))"
}

send_message() {
    local message="$1"

    message="${message//\'/\\\'}"
    printf "message-info '%s'\n" "${message}" > "${QUTE_FIFO}"
}

battery_path=''
for candidate in /sys/class/power_supply/BAT*; do
    if [[ -d "${candidate}" ]]; then
        battery_path="${candidate}"
        break
    fi
done

if [[ -z "${battery_path}" ]]; then
    send_message 'Battery: unavailable'
    exit 0
fi

message='Battery: unavailable'
capacity=''
if read_sysfs_value "${battery_path}/capacity"; then
    capacity="$(unsigned_value "${REPLY}")" || capacity=''
fi
if [[ -n "${capacity}" ]]; then
    message="Battery: ${capacity}%"
fi

status=''
if read_sysfs_value "${battery_path}/status"; then
    case "${REPLY}" in
        Charging|Discharging|Full|'Not charging'|Unknown)
            status="${REPLY}"
            ;;
    esac
fi
if [[ -n "${status}" ]]; then
    message+=" | Status: ${status}"
fi

power_uw=''
if read_sysfs_value "${battery_path}/power_now"; then
    power_uw="$(absolute_value "${REPLY}")" || power_uw=''
    [[ "${power_uw}" -gt 0 ]] || power_uw=''
fi

current_ua=''
if read_sysfs_value "${battery_path}/current_now"; then
    current_ua="$(absolute_value "${REPLY}")" || current_ua=''
    [[ "${current_ua}" -gt 0 ]] || current_ua=''
fi

if [[ -z "${power_uw}" && -n "${current_ua}" ]]; then
    voltage_uv=''
    if read_sysfs_value "${battery_path}/voltage_now"; then
        voltage_uv="$(absolute_value "${REPLY}")" || voltage_uv=''
    fi
    if [[ -n "${voltage_uv}" && "${voltage_uv}" -gt 0 ]]; then
        power_uw="$((current_ua * voltage_uv / 1000000))"
        [[ "${power_uw}" -gt 0 ]] || power_uw=''
    fi
fi

if [[ -n "${power_uw}" ]]; then
    power_watts="$(/usr/bin/awk -v microwatts="${power_uw}" 'BEGIN { printf "%.1f", microwatts / 1000000 }')"
    message+=" | Power draw: ${power_watts} W"
fi

remaining_minutes=''
if [[ "${status}" == 'Discharging' ]]; then
    if [[ -n "${power_uw}" ]] && read_sysfs_value "${battery_path}/energy_now"; then
        energy_uwh="$(unsigned_value "${REPLY}")" || energy_uwh=''
        if [[ -n "${energy_uwh}" && "${energy_uwh}" -gt 0 ]]; then
            remaining_minutes="$((energy_uwh * 60 / power_uw))"
        fi
    fi
    if [[ -z "${remaining_minutes}" && -n "${current_ua}" ]] \
        && read_sysfs_value "${battery_path}/charge_now"; then
        charge_uah="$(unsigned_value "${REPLY}")" || charge_uah=''
        if [[ -n "${charge_uah}" && "${charge_uah}" -gt 0 ]]; then
            remaining_minutes="$((charge_uah * 60 / current_ua))"
        fi
    fi
fi

if [[ -n "${remaining_minutes}" && "${remaining_minutes}" -gt 0 ]]; then
    message+=" | Estimated remaining: $((remaining_minutes / 60))h $((remaining_minutes % 60))m"
fi

send_message "${message}"
