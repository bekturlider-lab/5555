export class ApiError extends Error { constructor(public status:number, message:string) { super(message); } }
const csrf = () => decodeURIComponent(document.cookie.split('; ').find(c=>c.startsWith('campus_csrf='))?.split('=')[1] || '');
export async function api<T>(path:string, options:RequestInit={}):Promise<T> {
  const headers = new Headers(options.headers);
  if(options.body) headers.set('Content-Type','application/json');
  if(options.method && !['GET','HEAD'].includes(options.method)) headers.set('X-CSRF-Token',csrf());
  let response:Response;
  try { response=await fetch('/api/v1'+path,{...options,headers,credentials:'same-origin',signal:options.signal||AbortSignal.timeout(25000)}); }
  catch {throw new ApiError(0,'Не удалось связаться с банком. Проверьте соединение и попробуйте снова.');}
  if(!response.ok){
    const error=await response.json().catch(()=>({detail:'Не удалось выполнить запрос'}));
    if(response.status===428)window.dispatchEvent(new Event('campus:terms-required'));
    if(response.status===401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('campus:unauthorized'));
    throw new ApiError(response.status,typeof error.detail==='string'?error.detail:'Проверьте введённые данные');
  }
  return response.json();
}
export const send=<T,>(path:string,body:unknown,method='POST')=>api<T>(path,{method,body:JSON.stringify(body)});
export async function exportCsv(query:string){
  const r=await fetch('/api/v1/transactions/export?'+query,{credentials:'same-origin'});
  if(!r.ok){const e=await r.json();throw new Error(e.detail||'Выгрузка недоступна');}
  const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download='b-bank-statement.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
