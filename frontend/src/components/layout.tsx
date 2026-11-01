import {useEffect,useRef,useState} from 'react';
import {Link,NavLink,Outlet,Navigate,useLocation,useNavigate} from 'react-router-dom';
import {LayoutDashboard,WalletCards,CreditCard,ArrowLeftRight,Grid2X2,History,MessageCircle,Settings,ShieldCheck,Bell,LogOut,ChevronRight,Menu,X,Users,KeyRound,FileText,ArrowUpRight,ClipboardList} from 'lucide-react';
import {useAuth} from '../state/AuthProvider';
import {initials} from '../utils/money';
import {Loading,useAction} from './ui';
import {createLogoPressSequence} from '../utils/admin-shortcut';

export function Brand(){
 const {user}=useAuth();const navigate=useNavigate();const location=useLocation();
 const icon=useRef<HTMLButtonElement>(null);const[sequence]=useState(()=>createLogoPressSequence());
 useEffect(()=>{
  sequence.reset();
  const outside=(event:Event)=>{if(!icon.current?.contains(event.target as Node))sequence.reset();};
  const hidden=()=>{if(document.hidden)sequence.reset();};
  document.addEventListener('pointerdown',outside,true);document.addEventListener('click',outside,true);
  document.addEventListener('visibilitychange',hidden);window.addEventListener('blur',sequence.reset);
  return()=>{document.removeEventListener('pointerdown',outside,true);document.removeEventListener('click',outside,true);document.removeEventListener('visibilitychange',hidden);window.removeEventListener('blur',sequence.reset);};
 },[location.key,sequence]);
 return <div className="brand"><button ref={icon} type="button" className="brand-icon" aria-label="B bank — быстрый вход в панель управления: семь нажатий подряд" onBlur={sequence.reset} onKeyDown={e=>{if(e.repeat&&(e.key==='Enter'||e.key===' '))e.preventDefault();if(e.key==='Escape')sequence.reset();}} onClick={()=>{if(sequence.press(performance.now()))navigate(user&&user.role!=='client'?'/staff':'/login?next=%2Fstaff');}}><img src="/brand-assets/b-symbol.svg?v=4" alt=""/></button><Link to="/" className="brand-wordmark" aria-label="B bank — главная"><img src="/brand-assets/b-bank-wordmark.svg?v=4" alt=""/></Link></div>
}
export function Protected({staff=false}:{staff?:boolean}){const{user,loading}=useAuth();if(loading)return <Loading/>;if(!user)return <Navigate to="/login" replace/>;if(staff&&user.role==='client')return <Navigate to="/bank" replace/>;return <Outlet/>}
const clientNav=[['/bank','Главная',LayoutDashboard],['/bank/accounts','Счета',WalletCards],['/bank/cards','Карты',CreditCard],['/bank/transfers','Переводы',ArrowLeftRight],['/bank/payments','Платежи',Grid2X2],['/bank/history','История',History],['/bank/orders','Мои заявки',ClipboardList]] as const;
export function BankLayout({staff=false}:{staff?:boolean}){
 const{user,logout}=useAuth();const{busy,run}=useAction();const[menu,setMenu]=useState(false);const location=useLocation();
 const nav=staff?[['/staff','Обзор',LayoutDashboard],...(user?.role==='admin'?[['/staff/users','Клиенты',Users],['/staff/recovery','Восстановление',KeyRound],['/staff/audit','Журнал событий',FileText]]:[]),['/staff/orders','Заявки',ClipboardList],['/staff/tickets','Обращения',MessageCircle]]:clientNav;
 const title=nav.find(n=>n[0]===location.pathname)?.[1]||'Личный кабинет';
 return <div className="app-shell"><aside className={'sidebar '+(menu?'sidebar-open':'')}><div className="sidebar-brand"><Brand/><button className="icon-button mobile-only" aria-label="Закрыть меню" onClick={()=>setMenu(false)}><X size={21}/></button></div><div className="workspace-label">{staff?'РАБОЧЕЕ ПРОСТРАНСТВО':'ЛИЧНЫЙ КАБИНЕТ'}</div><nav aria-label="Основная навигация">{nav.map(([path,label,Icon])=><NavLink key={String(path)} to={String(path)} end={path==='/bank'||path==='/staff'} className={({isActive})=>'nav-item '+(isActive?'active':'')} onClick={()=>setMenu(false)}><Icon size={20}/><span>{String(label)}</span></NavLink>)}</nav><div className="sidebar-bottom">{!staff&&<><NavLink className="nav-item" to="/bank/support" onClick={()=>setMenu(false)}><MessageCircle size={20}/><span>Поддержка</span></NavLink><NavLink className="nav-item" to="/bank/profile" onClick={()=>setMenu(false)}><Settings size={20}/><span>Настройки</span></NavLink></>}{user?.role!=='client'&&<Link className="nav-item" to={staff?'/bank':'/staff'}><ArrowUpRight size={20}/><span>{staff?'Личный кабинет':'Кабинет сотрудника'}</span></Link>}<div className="environment"><ShieldCheck size={18}/><div><b>Учебная среда</b><span>Все деньги вымышленные</span></div></div><button className="nav-item logout" disabled={busy} onClick={()=>run(logout)}><LogOut size={18}/><span>Выйти</span></button></div></aside>{menu&&<div className="sidebar-backdrop" onClick={()=>setMenu(false)}/>}<div className="main-shell"><header className="topbar"><div className="topbar-left"><button className="icon-button mobile-only" onClick={()=>setMenu(true)} aria-label="Открыть меню"><Menu size={23}/></button><span className="breadcrumb">{staff?'B bank для сотрудников':'Личный кабинет'}</span><ChevronRight size={14}/><span>{String(title)}</span></div><div className="topbar-right"><span className="currency-badge">KGS</span><Link className="icon-button notification-icon" to="/bank/notifications" aria-label="Уведомления"><Bell size={21}/></Link><Link to="/bank/profile" className="profile-short"><span className="avatar avatar-small">{initials(user?.full_name||'')}</span><span>{user?.full_name.split(' ')[0]}</span></Link></div></header><main className="page-container" key={location.pathname}><Outlet/></main><footer className="app-footer"><span>© 2026 B bank</span><Link to="/agreements">Соглашения и условия</Link></footer></div></div>
}
