import {Routes,Route} from 'react-router-dom';
import {Protected,BankLayout} from './components/layout';
import {LoginPage,RecoveryPage,NotFoundPage} from './pages/public';
import {DashboardPage} from './pages/dashboard';
import {AccountsPage,CardsPage} from './pages/accounts-cards';
import {OperationPage} from './pages/operations';
import {HistoryPage,TransactionPage} from './pages/history';
import {ProfilePage,SessionsPage} from './pages/profile';
import {SupportPage,TicketPage,NotificationsPage} from './pages/support-notifications';
import {StaffDashboardPage,UsersPage,UserPage,RecoveryRequestsPage,AuditPage} from './pages/staff';
import {PublicLayout} from './components/public-layout';
import {MarketingHomePage,CatalogPage,ProductPage,PromotionsPage,AboutPage,TeamPage,ContactsPage} from './pages/public-site';
import {RegisterPage,ApplyPage,OrdersPage} from './pages/registration-orders';
import {AgreementsPage,FeaturesPage} from './components/agreements';
import {BrandPage} from './pages/brand';
export default function App(){return <Routes><Route element={<PublicLayout/>}><Route path="/" element={<MarketingHomePage/>}/><Route path="/products" element={<CatalogPage/>}/><Route path="/products/:id" element={<ProductPage/>}/><Route path="/promotions" element={<PromotionsPage/>}/><Route path="/about" element={<AboutPage/>}/><Route path="/team" element={<TeamPage/>}/><Route path="/contacts" element={<ContactsPage/>}/><Route path="/features" element={<FeaturesPage/>}/><Route path="/brand" element={<BrandPage/>}/><Route path="/agreements" element={<AgreementsPage/>}/><Route path="/apply/:id" element={<ApplyPage/>}/></Route><Route path="/register" element={<RegisterPage/>}/><Route path="/login" element={<LoginPage/>}/><Route path="/recover" element={<RecoveryPage/>}/><Route element={<Protected/>}><Route path="/bank" element={<BankLayout/>}><Route index element={<DashboardPage/>}/><Route path="orders" element={<OrdersPage/>}/><Route path="accounts" element={<AccountsPage/>}/><Route path="cards" element={<CardsPage/>}/><Route path="transfers" element={<OperationPage/>}/><Route path="payments" element={<OperationPage payment/>}/><Route path="history" element={<HistoryPage/>}/><Route path="history/:id" element={<TransactionPage/>}/><Route path="profile" element={<ProfilePage/>}/><Route path="profile/sessions" element={<SessionsPage/>}/><Route path="support" element={<SupportPage/>}/><Route path="support/:id" element={<TicketPage/>}/><Route path="notifications" element={<NotificationsPage/>}/></Route></Route><Route element={<Protected staff/>}><Route path="/staff" element={<BankLayout staff/>}><Route index element={<StaffDashboardPage/>}/><Route path="orders" element={<OrdersPage staff/>}/><Route path="users" element={<UsersPage/>}/><Route path="users/:id" element={<UserPage/>}/><Route path="tickets" element={<SupportPage staff/>}/><Route path="tickets/:id" element={<TicketPage staff/>}/><Route path="recovery" element={<RecoveryRequestsPage/>}/><Route path="audit" element={<AuditPage/>}/></Route></Route><Route path="*" element={<NotFoundPage/>}/></Routes>}
