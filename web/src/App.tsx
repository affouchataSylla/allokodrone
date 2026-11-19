import { BrowserRouter, Route, Routes } from "react-router";
import { BASE } from "./base";
import { Shell } from "./Shell";
import { SessionProvider } from "./session";
import { Account } from "./pages/Account";
import { AdminRedirect } from "./pages/AdminRedirect";
import { Cart } from "./pages/Cart";
import { Checkout } from "./pages/Checkout";
import { Avis, Concept, Guide, Signature } from "./pages/Chapters";
import { Contact } from "./pages/Contact";
import { Home } from "./pages/Home";
import { Menu } from "./pages/Menu";
import { NotFound } from "./pages/NotFound";
import { Order } from "./pages/Order";
import { PaymentFailure, PaymentSuccess } from "./pages/Payment";
import { Product } from "./pages/Product";
import { PromotionAdmin } from "./pages/PromotionAdmin";

export function App() {
  return (
    <BrowserRouter basename={BASE.replace(/\/$/, "") || undefined}>
      <SessionProvider>
        <Routes>
          <Route path="/admin/promotions" element={<PromotionAdmin />} />
          <Route path="/admin" element={<AdminRedirect />} />
          <Route path="/admin/*" element={<AdminRedirect />} />
          <Route element={<Shell />}>
            <Route path="/" element={<Home />} />
            <Route path="/histoire" element={<Concept />} />
            <Route path="/concept" element={<Concept />} />
            <Route path="/signature" element={<Signature />} />
            <Route path="/carte" element={<Menu />} />
            <Route path="/passer -commande" element={<Guide />} />
            <Route path="/avis" element={<Avis />} />
            <Route path="/produit/:slug" element={<Product />} />
            <Route path="/panier" element={<Cart />} />
            <Route path="/commander" element={<Checkout />} />
            <Route path="/commande/:ref" element={<Order />} />
            <Route path="/paiement/succes" element={<PaymentSuccess />} />
            <Route path="/paiement/echec" element={<PaymentFailure />} />
            <Route path="/compte" element={<Account />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </SessionProvider>
    </BrowserRouter>
  );
}
