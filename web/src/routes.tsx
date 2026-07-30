import { Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import Footer from "./components/Footer";
import HomePage from "./pages/HomePage";
import CollectionsPage from "./pages/CollectionsPage";
import CollectionPage from "./pages/CollectionPage";
import FindingsPage from "./pages/FindingsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function AppRoutes() {
  return (
    <div className="flex min-h-screen w-full flex-col">
      <Header />
      <main className="grow">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/collections" element={<CollectionsPage />} />
          <Route path="/collections/:slug" element={<CollectionPage />} />
          <Route path="/where-did-the-money-go" element={<FindingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}
