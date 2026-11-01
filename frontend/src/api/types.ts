export interface User {id:string; username:string; full_name:string; email:string; role:'client'|'staff'|'admin'; status:string; created_at:string}
export interface Account {id:string; reference:string; name:string; kind:string; balance:number; status:string; currency:string}
export interface Card {id:string; account_id:string; account_name:string; account_reference:string; balance:number; label:string; last4:string; color:string; status:string; daily_limit:number}
export interface Transaction {id:string; reference:string; amount:number; direction:'incoming'|'outgoing'|'internal'; kind:string; description:string; category:string; counterparty:string; from_reference:string; to_reference:string; customer_reference:string; created_at:string; status:string; fee:number}
export interface Page<T> {items:T[]; total:number; page:number; page_size:number}
export interface Intent {id:string; amount:number; fee:number; description:string; recipient:string; to_reference:string; customer_reference:string; expires_at:string; kind:string}
export interface Provider {id:string; name:string; category:string; color:string; icon:string}
export interface BankNotification {id:string; title:string; body:string; link:string; is_read:boolean; created_at:string}
export interface Ticket {id:string; title:string; category:string; status:string; client_name:string; created_at:string; updated_at:string; messages?:{id:string; body:string; author:string; role:string; created_at:string}[]}
export interface Dashboard {balance:number; income:number; spent:number; accounts:Account[]; cards:Card[]; transactions:Transaction[]; categories:{name:string;amount:number}[]; daily:{date:string;amount:number}[]; contacts:{reference:string;full_name:string}[]; unread:number}
export interface Session {id:string; user_agent:string; created_at:string; expires_at:string; current:boolean}
export interface Recovery {id:string; username:string; full_name:string; status:string; created_at:string; expires_at:string|null}
export interface Audit {id:string; action:string; actor:string; entity_id:string; details:Record<string,unknown>; created_at:string}
