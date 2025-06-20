import { Message } from '@arco-design/web-vue'
import { apiPrefix, httpCode } from '@/config'
import { useCredentialStore } from '@/stores/credential'
import router from '@/router'

// 1.超时时间为100s
const TIME_OUT = 100000

// 2.基础的配置
const baseFetchOptions = {
  method: 'GET',
  mode: 'cors',
  credentials: 'include',
  headers: new Headers({
    'Content-Type': 'application/json',
  }),
  redirect: 'follow',
}

// 3.fetch参数类型
type FetchOptionType = Omit<RequestInit, 'body'> & {
  params?: Record<string, any>
  body?: BodyInit | Record<string, any> | null
}

// 4.封装基础的fetch请求
const baseFetch = <T>(url: string, fetchOptions: FetchOptionType): Promise<T> => {
  // 5.将所有的配置信息合并起来
  const options: typeof baseFetchOptions & FetchOptionType = Object.assign(
    {},
    baseFetchOptions,
    fetchOptions,
  )
  const { credential, clear: clearCredential } = useCredentialStore()
  const access_token = credential.access_token
  if (access_token) options.headers.set('Authorization', `Bearer ${access_token}`)

  // 6.组装url
  let urlWithPrefix = `${apiPrefix}${url.startsWith('/') ? url : `/${url}`}`

  // 7.解构出对应的请求方法、params、body参数
  const { method, params, body } = options

  // 8.如果请求是GET方法，并且传递了params参数
  if (method === 'GET' && params) {
    const paramsArray: string[] = []
    Object.keys(params).forEach((key) => {
      paramsArray.push(`${key}=${encodeURIComponent(params[key])}`)
    })
    if (urlWithPrefix.search(/\?/) === -1) {
      urlWithPrefix += `?${paramsArray.join('&')}`
    } else {
      urlWithPrefix += `&${paramsArray.join('&')}`
    }

    delete options.params
  }

  // 9.处理post传递的数据
  if (body) {
    options.body = JSON.stringify(body)
  }

  // 10.同时发起两个Promise(或者是说两个操作，看谁先返回，就先结束)
  return Promise.race([
    // 11.使用定时器来检测是否超时
    new Promise((resolve, reject) => {
      setTimeout(() => {
        reject('接口已超时')
      }, TIME_OUT)
    }),
    // 12.发起一个正常请求
    new Promise((resolve, reject) => {
      globalThis
        .fetch(urlWithPrefix, options as RequestInit)
        .then(async (res) => {
          const json = await res.json()
          if (json.code === httpCode.success) {
            resolve(json)
          } else if (json.code === httpCode.unauthorized) {
            clearCredential()
            await router.replace({ name: 'auth-login' })
          } else if (json.code === httpCode.notFound) {
            await router.push({ name: 'errors-not-found' })
          } else if (json.code === httpCode.forbidden) {
            await router.push({ name: 'errors-forbidden' })
          } else {
            Message.error(json.message)
            reject(new Error(json.message))
          }
        })
        .catch((err) => {
          Message.error(err.message)
          reject(err)
        })
    }),
  ]) as Promise<T>
}

// 5.封装基于post的sse(流式事件响应)请求
export const ssePost = async (
  url: string,
  fetchOptions: FetchOptionType,
  onData: (data: { [key: string]: any }) => void,
) => {
  // 5.1 组装基础的fetch请求配置
  const options = Object.assign({}, baseFetchOptions, { method: 'POST' }, fetchOptions)
  const { credential } = useCredentialStore()
  const access_token = credential.access_token
  if (access_token) options.headers.set('Authorization', `Bearer ${access_token}`)

  // 5.2 组装请求URL
  const urlWithPrefix = `${apiPrefix}${url.startsWith('/') ? url : `/${url}`}`

  // 5.3 结构body参数，并处理body对应的数据
  const { body } = fetchOptions
  if (body) options.body = JSON.stringify(body)

  // 5.4 发起fetch请求并处理流式事件响应
  const response = await globalThis.fetch(urlWithPrefix, options as RequestInit)

  // 5.5 获取响应内容类型并判断类型
  const contentType = response.headers.get('Content-Type')
  if (contentType?.includes('application/json')) {
    // 5.6 接口为json输出，意味着出错，直接返回json数据
    return await response.json()
  }

  // 5.7 否则获取流式输出数据
  return await handleStream(response, onData)
}

const handleStream = (
  response: Response,
  onData: (data: Record<string, any>) => void,
): Promise<void> => {
  return new Promise((resolve, reject) => {
    // 1.检测网络请求是否正常
    if (!response.ok) {
      reject(new Error('网络请求失败'))
      return
    }

    // 2.构建reader以及decoder
    const reader = response.body?.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let event = ''
    let data = ''

    // 3.构建read函数用于去读取数据
    const read = () => {
      reader?.read().then((result: any) => {
        if (result.done) {
          resolve()
          return
        }

        buffer += decoder.decode(result.value, { stream: true })
        const lines = buffer.split('\n')

        try {
          lines.forEach((line) => {
            line = line.trim()
            if (line.startsWith('event:')) {
              event = line.slice(6).trim()
            } else if (line.startsWith('data:')) {
              data = line.slice(5).trim()
            }

            // 每个事件以空行结束，只有event和data同时存在，才表示一次流式事件的数据完整获取到了
            if (line === '') {
              if (event !== '' && data !== '') {
                onData({
                  event: event,
                  data: JSON.parse(data),
                })
                event = ''
                data = ''
              }
            }
          })
          buffer = lines.pop() || ''
        } catch (e) {
          reject(e)
        }

        read()
      })
    }

    // 4.调用read函数去执行获取对应的数据
    read()
  })
}

export const upload = <T>(url: string, options: any = {}): Promise<T> => {
  // 1 组装请求URL
  const urlWithPrefix = `${apiPrefix}${url.startsWith('/') ? url : `/${url}`}`

  // 2.组装xhr请求配置信息
  const defaultOptions = {
    method: 'POST',
    url: urlWithPrefix,
    headers: {},
    data: {},
  }
  options = {
    ...defaultOptions,
    ...options,
    headers: { ...defaultOptions.headers, ...options.headers },
  }
  const { credential, clear: clearCredential } = useCredentialStore()
  const access_token = credential.access_token
  if (access_token) options.headers['Authorization'] = `Bearer ${access_token}`

  // 3.构建promise并使用xhr完成文件上传
  return new Promise((resolve, reject) => {
    // 4.创建xhr服务
    const xhr = new XMLHttpRequest()

    // 5.初始化xhr请求并配置headers
    xhr.open(options.method, options.url)
    for (const key in options.headers) {
      xhr.setRequestHeader(key, options.headers[key])
    }

    // 6.设置xhr响应格式并携带授权凭证（例如cookie）
    xhr.withCredentials = true
    xhr.responseType = 'json'

    // 7.监听xhr状态变化并导出数据
    xhr.onreadystatechange = async () => {
      // 8.判断xhr的状态是不是为4，如果为4则代表已经传输完成（涵盖成功与失败）
      if (xhr.readyState === 4) {
        // 9.检查响应状态码，当HTTP状态码为200的时候表示请求成功
        if (xhr.status === 200) {
          // 10.判断业务状态码是否正常
          const response = xhr.response
          if (response.code === httpCode.success) {
            resolve(response)
          } else if (response.code === httpCode.unauthorized) {
            clearCredential()
            await router.replace({ path: '/auth/login' })
          } else {
            reject(xhr.response)
          }
        } else {
          reject(xhr)
        }
      }
    }

    // 10.添加xhr进度监听
    xhr.upload.onprogress = options.onprogress

    // 11.发送请求
    xhr.send(options.data)
  })
}

export const request = <T>(url: string, options = {}) => {
  return baseFetch<T>(url, options)
}

export const get = <T>(url: string, options = {}) => {
  return request<T>(url, Object.assign({}, options, { method: 'GET' }))
}

export const post = <T>(url: string, options = {}) => {
  return request<T>(url, Object.assign({}, options, { method: 'POST' }))
}
