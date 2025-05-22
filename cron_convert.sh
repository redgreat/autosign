#!/bin/bash

function inspect_hours {
  cron_str=$1
  cron_hours=$(echo "$cron_str" | awk '{print $2}')
  echo "$cron_hours"
}

function inspect_next {
  cron_str=$1
  cron_str="${cron_str//\'/}"
  minute=$(TZ=UTC date '+%M')
  minute=$((10#$minute))
  hour=$(TZ=UTC date '+%H')
  hour=$((10#$hour))
  cron_minute=$(echo "$cron_str" | awk '{print $1}')
  cron_hours=$(echo "$cron_str" | awk '{print $2}')
  # echo "current $hour:$minute"
  # echo "cron hours: $cron_hours"
  next_exec_hour=$(echo "$cron_hours" | awk -v min="$minute" -v hour="$hour" -v cron_min="$cron_minute" -F ',' '{
    for (i=1;i<=NF;i++) {
      if ($i>hour || $i==hour && cron_min>min) {
         print $i
         break
      }
    }
  }')
  if test -z "$next_exec_hour"; then
    next_exec_hour=$(echo "$cron_hours" | awk -F ',' '{print $1}')
  fi
  echo "next exec time: UTC($next_exec_hour:$cron_minute) 北京时间($(((next_exec_hour + 8) % 24)):$cron_minute)"
}

function hours_except_now {
  cron_hours=$1
  hour=$(TZ=UTC date '+%H')
  hour=$((10#$hour))
  except_current_hours=$(echo "$cron_hours" | awk -v hour="$hour" -F ',' '{
    for (i=1;i<=NF;i++) {
      if ($i!=hour) {
        print $i
      }
    }
  }')
  result=""
  while IFS= read -r line; do
    if [ -z "$result" ]; then
      result="$line"
    else
      result="$result,$line"
    fi
  done <<< "$except_current_hours"
  if test -z "$result"; then
    # 只有一个小时，则直接返回当前值
    result=$cron_hours
  fi
  echo "$result"
}

function convert_utc_to_shanghai {
  local cron_str=$1
  echo "UTC时间: ${cron_str}"
  minute=$(echo "$cron_str" | awk '{print $1}')
  hours=$(echo "$cron_str" | awk '{print $2}')
  lines=$(echo "$hours"|awk -F ',' '{for (i=1;i<=NF;i++) { print ($i+8)%24 }}')
  # echo $lines
  result=""
  while IFS= read -r line; do
    if [ -z "$result" ]; then
      result="$line"
    else
      result="$result,$line"
    fi
  done <<< "$lines"
  echo "北京时间: $minute $result * * *'"
}

function persist_execute_log {
  local event_name=$1
  local new_cron_hours=$2
  echo "trigger by: ${event_name}" > cron_change_time
  {
    echo "current system time:"
    TZ='UTC' date "+%y-%m-%d %H:%M:%S" | xargs -I {} echo "UTC: {}"
    TZ='Asia/Shanghai' date "+%y-%m-%d %H:%M:%S" | xargs -I {} echo "北京时间: {}"
  } >> cron_change_time
  current_cron=$(< .github/workflows/run.yml grep cron|awk '{print substr($0, index($0,$3))}')
  {
    echo "current cron:"
    convert_utc_to_shanghai "$current_cron"
  } >> cron_change_time
  os=$(uname -s)
  sed_prefix=(sed -i)
  if [[ $os == "Darwin" ]]; then
    sed_prefix=(sed -i '')
  fi

  # 如果是由 workflow_run 触发的（即签到成功后），则设置为第二天的时间
  if [[ "$event_name" == "workflow_run" ]]; then
    # 获取当前UTC时间的小时
    current_hour=$(TZ=UTC date '+%H')
    current_hour=$((10#$current_hour))

    # 选择第二天的时间点（UTC 1-4点之间的随机小时，对应北京时间 9-12点）
    random_hour=$((1 + RANDOM % 4))
    random_minute=$((RANDOM % 59))

    # 如果当前时间已经超过了设置的时间，确保cron表达式使用明天的日期
    if [[ $current_hour -ge $random_hour ]]; then
      # 当前时间已经超过了随机选择的小时，使用明天的日期
      tomorrow=$(TZ=UTC date -d "tomorrow" '+%d')
      "${sed_prefix[@]}" -E "s/(- cron: ')[0-9]+( [0-9]+ \* \* \*')/\1${random_minute} ${random_hour} ${tomorrow} * *'/g" .github/workflows/run.yml
    else
      # 当前时间还没超过随机选择的小时，使用标准格式（每天执行）
      "${sed_prefix[@]}" -E "s/(- cron: ')[0-9]+( [^[:space:]]+ \* \* \*')/\1${random_minute} ${random_hour} * * *'/g" .github/workflows/run.yml
    fi
  else
    # 如果是手动触发或其他情况，保持原来的逻辑
    current_cron=$(< .github/workflows/run.yml grep cron|awk '{print substr($0, index($0,$3))}')
    cron_hours=$(inspect_hours "$current_cron")
    if test -n "$new_cron_hours"; then
      cron_hours=$(hours_except_now "$new_cron_hours")
    fi
    "${sed_prefix[@]}" -E "s/(- cron: ')[0-9]+( [^[:space:]]+ \* \* \*')/\1$((RANDOM % 59)) ${cron_hours} * * *'/g" .github/workflows/run.yml
  fi

  current_cron=$(< .github/workflows/run.yml grep cron|awk '{print substr($0, index($0,$3))}')
  {
    echo "next cron:"
    convert_utc_to_shanghai "$current_cron"
    inspect_next "$current_cron"
  } >> cron_change_time
}
