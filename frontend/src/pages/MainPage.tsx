import { useEffect, useState } from 'react'
import {
  Layout, Select, DatePicker, TimePicker, Input, Table, Image, Typography, Button, Space, theme
} from 'antd'
import { LogoutOutlined, FileExcelOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs, { Dayjs } from 'dayjs'
import * as XLSX from 'xlsx'
import { getGroups, getRecords } from '../api/records'
import { logout } from '../api/auth'

type RecordItem = {
  id: number
  plate_number: string
  group_name: string
  status: string
  created_at: string
  crop_url: string | null
  original_url: string | null
}

const { Header, Content } = Layout
const { RangePicker } = DatePicker

export default function MainPage() {
  const navigate = useNavigate()
  const { token } = theme.useToken()

  const [groups, setGroups] = useState<string[]>([])
  const [group, setGroup] = useState<string | undefined>()
  const [search, setSearch] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  const [dates, setDates] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [times, setTimes] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [data, setData] = useState<RecordItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<RecordItem | null>(null)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearchDebounced(search)
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [search])

  const buildDateTimeParams = () => {
    let date_from: string | undefined
    let date_to: string | undefined
    const timeFrom = times?.[0]
    const timeTo = times?.[1]
    const dayFrom = dates?.[0]
    const dayTo = dates?.[1]

    if (dayFrom) {
      const d = dayFrom
        .hour(timeFrom ? timeFrom.hour() : 0)
        .minute(timeFrom ? timeFrom.minute() : 0)
        .second(0)
      date_from = d.format('YYYY-MM-DDTHH:mm:ss')
    }
    if (dayTo) {
      const d = dayTo
        .hour(timeTo ? timeTo.hour() : 23)
        .minute(timeTo ? timeTo.minute() : 59)
        .second(59)
      date_to = d.format('YYYY-MM-DDTHH:mm:ss')
    }
    return { date_from, date_to }
  }

  const loadGroups = async () => {
    try {
      const list = await getGroups()
      setGroups(list)
    } catch {
      navigate('/login')
    }
  }

  const loadRecords = async () => {
    setLoading(true)
    try {
      const { date_from, date_to } = buildDateTimeParams()
      const res = await getRecords({
        group,
        search: searchDebounced || undefined,
        date_from,
        date_to,
        page,
      })
      setData(res.results)
      setTotal(res.count)
    } catch {
      navigate('/login')
    } finally {
      setLoading(false)
    }
  }

  const exportExcel = async () => {
    setExporting(true)
    try {
      const { date_from, date_to } = buildDateTimeParams()
      // забираем несколько страниц по текущим фильтрам
      const all: RecordItem[] = []
      let pageNum = 1
      let hasNext = true
      while (hasNext && pageNum <= 50) {
        const res = await getRecords({
          group,
          search: searchDebounced || undefined,
          date_from,
          date_to,
          page: pageNum,
        })
        all.push(...res.results)
        hasNext = !!res.next
        pageNum += 1
      }

      const rows = all.map((r) => ({
        ID: r.id,
        Номер: r.plate_number,
        Группа: r.group_name,
        Дата: dayjs(r.created_at).format('DD.MM.YYYY HH:mm'),
        Статус: r.status,
      }))

      const ws = XLSX.utils.json_to_sheet(rows)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'Номера')
      XLSX.writeFile(wb, `numbers_${dayjs().format('YYYYMMDD_HHmm')}.xlsx`)
    } catch {
      navigate('/login')
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    loadGroups()
  }, [])

  useEffect(() => {
    loadRecords()
  }, [group, searchDebounced, dates, times, page])

  useEffect(() => {
    const id = setInterval(() => loadRecords(), 15000)
    return () => clearInterval(id)
  }, [group, searchDebounced, dates, times, page])

  const columns = [
    {
      title: 'Номер',
      dataIndex: 'plate_number',
      key: 'plate_number',
      width: 140,
      render: (text: string) => <b>{text}</b>,
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: 'Группа',
      dataIndex: 'group_name',
      key: 'group_name',
      width: 140,
    },
    {
      title: 'Кроп',
      dataIndex: 'crop_url',
      key: 'crop_url',
      width: 120,
      render: (url: string | null) =>
        url ? <Image src={url} height={36} style={{ borderRadius: 4 }} /> : '—',
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          background: token.colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          padding: '12px 20px',
          height: 'auto',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <Typography.Text strong style={{ marginRight: 8 }}>
          Номера
        </Typography.Text>

        <Select
          allowClear
          placeholder="Группа"
          style={{ width: 180 }}
          value={group}
          onChange={(v) => {
            setGroup(v)
            setPage(1)
          }}
          options={groups.map((g) => ({ value: g, label: g }))}
        />

        <RangePicker
          value={dates}
          onChange={(v) => {
            setDates(v)
            setPage(1)
          }}
          placeholder={['Дата от', 'Дата до']}
        />

        <TimePicker.RangePicker
          value={times}
          onChange={(v) => {
            setTimes(v)
            setPage(1)
          }}
          format="HH:mm"
          placeholder={['Время от', 'Время до']}
        />

        <Input
          placeholder="Поиск номера"
          allowClear
          style={{ width: 200 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <Button
          icon={<FileExcelOutlined />}
          loading={exporting}
          onClick={exportExcel}
        >
          Excel
        </Button>

        <div style={{ flex: 1 }} />

        <Button
          icon={<LogoutOutlined />}
          onClick={() => {
            logout()
            navigate('/login')
          }}
        >
          Выйти
        </Button>
      </Header>

      <Content style={{ display: 'flex', gap: 16, padding: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Table
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={data}
            pagination={{
              current: page,
              total,
              pageSize: 20,
              onChange: setPage,
              showSizeChanger: false,
            }}
            onRow={(record) => ({
              onClick: () => setSelected(record),
              style: {
                cursor: 'pointer',
                background:
                  selected?.id === record.id ? token.colorPrimaryBg : undefined,
              },
            })}
            size="middle"
          />
        </div>

        <div
          style={{
            width: 380,
            background: token.colorBgContainer,
            borderRadius: 8,
            border: `1px solid ${token.colorBorderSecondary}`,
            padding: 16,
          }}
        >
          {selected ? (
            <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
              <Typography.Title level={4} style={{ margin: 0 }}>
                {selected.plate_number}
              </Typography.Title>
              <Typography.Text type="secondary">
                {selected.group_name} ·{' '}
                {dayjs(selected.created_at).format('DD.MM.YYYY HH:mm')}
              </Typography.Text>

              {selected.original_url ? (
                <Image
                  src={selected.original_url}
                  style={{ width: '100%', borderRadius: 8 }}
                />
              ) : (
                <Typography.Text type="secondary">Нет изображения</Typography.Text>
              )}

              {selected.crop_url && (
                <div>
                  <Typography.Text type="secondary">Кроп</Typography.Text>
                  <div style={{ marginTop: 8 }}>
                    <Image
                      src={selected.crop_url}
                      style={{ maxHeight: 80, borderRadius: 4 }}
                    />
                  </div>
                </div>
              )}
            </Space>
          ) : (
            <Typography.Text type="secondary">
              Выберите запись в таблице
            </Typography.Text>
          )}
        </div>
      </Content>
    </Layout>
  )
}