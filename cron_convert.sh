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
    result=$cron_hours
  fi
  echo "$result"
}

function convert_utc_to_shanghai {
  local cron_str=$1
  echo "UTC时间: ${cron_str}"
  minute=$(echo "$cron_str" | awk '{print $1}')
  hours=$(echo "$cron_str" | awk '{print $2}')
  day=$(echo "$cron_str" | awk '{print $3}')
  month=$(echo "$cron_str" | awk '{print $4}')
  
  # 如果是具体日期格式
  if [[ "$day" != "*" && "$month" != "*" ]]; then
    # 转换小时
    shanghai_hour=$((hours + 8))
    shanghai_day=$day
    shanghai_month=$month
    
    # 处理跨日情况
    if [[ $shanghai_hour -ge 24 ]]; then
      shanghai_hour=$((shanghai_hour - 24))
      shanghai_day=$((day + 1))
      # 简化处理月份跨越
      if [[ $shanghai_day -gt 31 ]]; then
        shanghai_day=1
        shanghai_month=$((month + 1))
        if [[ $shanghai_month -gt 12 ]]; then
          shanghai_month=1
        fi
      fi
    fi
    
    echo "北京时间: $minute $shanghai_hour $shanghai_day $shanghai_month *'"
  else
    # 原来的处理方式，用于通用时间格式
    lines=$(echo "$hours"|awk -F ',' '{for (i=1;i<=NF;i++) { print ($i+8)%24 }}')
    result=""
    while IFS= read -r line; do
      if [ -z "$result" ]; then
        result="$line"
      else
        result="$result,$line"
      fi
    done <<< "$lines"
    echo "北京时间: $minute $result * * *'"
  fi
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

  if [[ "$event_name" == "workflow_run" ]]; then
    # 获取东八区当前时间
    current_hour=$(TZ=Asia/Shanghai date '+%H')
    current_hour=$((10#$current_hour))
    current_minute=$(TZ=Asia/Shanghai date '+%M')
    current_minute=$((10#$current_minute))
    current_day=$(TZ=Asia/Shanghai date '+%d')
    current_day=$((10#$current_day))
    current_month=$(TZ=Asia/Shanghai date '+%m')
    current_month=$((10#$current_month))

    echo "当前东八区时间: ${current_hour}:${current_minute} 日期: ${current_month}月${current_day}日"

    # 计算东八区明天的日期
    tomorrow_timestamp=$(TZ=Asia/Shanghai date -d "+1 day" '+%s')
    tomorrow_day=$(TZ=Asia/Shanghai date -d "@${tomorrow_timestamp}" '+%d')
    tomorrow_day=$((10#$tomorrow_day))
    tomorrow_month=$(TZ=Asia/Shanghai date -d "@${tomorrow_timestamp}" '+%m')
    tomorrow_month=$((10#$tomorrow_month))

    # 生成随机的执行时间（东八区8-11点之间）
     random_minute=$((RANDOM % 59))
     random_hour=$((RANDOM % 4 + 8))
    
    # 将东八区时间转换为UTC时间
    utc_hour=$((random_hour - 8))
    if [[ $utc_hour -lt 0 ]]; then
      utc_hour=$((utc_hour + 24))
      # 如果UTC时间是前一天，需要调整日期
      utc_day=$((tomorrow_day - 1))
      utc_month=$tomorrow_month
      if [[ $utc_day -le 0 ]]; then
        utc_month=$((tomorrow_month - 1))
        if [[ $utc_month -le 0 ]]; then
          utc_month=12
        fi
        # 获取上个月的最后一天
        if [[ $utc_month -eq 2 ]]; then
          utc_day=28  # 简化处理，假设2月28天
        elif [[ $utc_month -eq 4 || $utc_month -eq 6 || $utc_month -eq 9 || $utc_month -eq 11 ]]; then
          utc_day=30
        else
          utc_day=31
        fi
      fi
    else
      utc_day=$tomorrow_day
      utc_month=$tomorrow_month
    fi
    
    echo "设置为明天东八区时间: ${random_hour}:${random_minute} (${tomorrow_month}月${tomorrow_day}日)"
    echo "对应UTC时间: ${utc_hour}:${random_minute} (${utc_month}月${utc_day}日)"
    
    # 使用具体日期的cron表达式，格式：分 时 日 月 *
    "${sed_prefix[@]}" -E "s/(- cron: ')[0-9]+( [0-9]+ [0-9]+ [0-9]+ \*')/\1${random_minute} ${utc_hour} ${utc_day} ${utc_month} *'/g" .github/workflows/run.yml
    # 如果上面的替换没有匹配到，尝试匹配原来的格式
    "${sed_prefix[@]}" -E "s/(- cron: ')[0-9]+( [^[:space:]]+ \* \* \*')/\1${random_minute} ${utc_hour} ${utc_day} ${utc_month} *'/g" .github/workflows/run.yml
  else
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
