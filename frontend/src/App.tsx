/** 路由表：登录页 + 主框架下的 9 个页面组（一期共 28 条路由）。 */
import { Navigate, Route, Routes } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import RequireAdmin from '@/components/RequireAdmin'
import Home from '@/pages/Home'
import Login from '@/pages/Login'
import Profile from '@/pages/Profile'
import MaterialList from '@/pages/materials/MaterialList'
import MaterialForm from '@/pages/materials/MaterialForm'
import MaterialImport from '@/pages/materials/MaterialImport'
import MaterialReview from '@/pages/materials/MaterialReview'
import MaterialClasses from '@/pages/materials/MaterialClasses'
import Tags from '@/pages/materials/Tags'
import TopicList from '@/pages/topics/TopicList'
import TopicGenerate from '@/pages/topics/TopicGenerate'
import TopicBatches from '@/pages/topics/TopicBatches'
import TopicForm from '@/pages/topics/TopicForm'
import TopicDetail from '@/pages/topics/TopicDetail'
import ScriptList from '@/pages/scripts/ScriptList'
import ScriptGenerate from '@/pages/scripts/ScriptGenerate'
import ScriptForm from '@/pages/scripts/ScriptForm'
import ScriptReview from '@/pages/scripts/ScriptReview'
import ScriptDetail from '@/pages/scripts/ScriptDetail'
import ScriptVersions from '@/pages/scripts/ScriptVersions'
import DataSources from '@/pages/analysis/DataSources'
import RawData from '@/pages/analysis/RawData'
import AnalysisTasks from '@/pages/analysis/AnalysisTasks'
import AnalysisTaskDetail from '@/pages/analysis/AnalysisTaskDetail'
import Users from '@/pages/admin/Users'
import AdminPromptTemplates from '@/pages/admin/PromptTemplates'
import BenchmarkAccounts from '@/pages/collection/BenchmarkAccounts'
import CollectionTasks from '@/pages/collection/CollectionTasks'
import ResearchTasks from '@/pages/research/ResearchTasks'
import ResearchReport from '@/pages/research/ResearchReport'
import ReportList from '@/pages/reports/ReportList'
import ReportDetail from '@/pages/reports/ReportDetail'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<MainLayout />}>
        <Route path="/" element={<Home />} />

        {/* 模块 01 资料库 */}
        <Route path="/materials" element={<MaterialList />} />
        <Route path="/materials/new" element={<MaterialForm />} />
        <Route path="/materials/import" element={<MaterialImport />} />
        <Route path="/materials/review" element={<MaterialReview />} />
        <Route path="/materials/:id" element={<MaterialForm />} />
        <Route path="/material-classes" element={<MaterialClasses />} />
        <Route path="/tags" element={<Tags />} />

        {/* 模块 02 选题库 */}
        <Route path="/topics" element={<TopicList />} />
        <Route path="/topics/generate" element={<TopicGenerate />} />
        <Route path="/topics/batches" element={<TopicBatches />} />
        <Route path="/topics/new" element={<TopicForm />} />
        <Route path="/topics/:id" element={<TopicDetail />} />
        <Route path="/topics/:id/edit" element={<TopicForm />} />

        {/* 模块 03 脚本库 */}
        <Route path="/scripts" element={<ScriptList />} />
        <Route path="/scripts/generate" element={<ScriptGenerate />} />
        <Route path="/scripts/new" element={<ScriptForm />} />
        <Route path="/scripts/review" element={<ScriptReview />} />
        <Route path="/scripts/:id" element={<ScriptDetail />} />
        <Route path="/scripts/:id/edit" element={<ScriptForm />} />
        <Route path="/scripts/:id/versions" element={<ScriptVersions />} />

        {/* 模块 04 数据分析 */}
        <Route path="/analysis/data-sources" element={<DataSources />} />
        <Route path="/analysis/raw-data" element={<RawData />} />
        <Route path="/analysis/tasks" element={<AnalysisTasks />} />
        <Route path="/analysis/tasks/:id" element={<AnalysisTaskDetail />} />
        <Route path="/reports" element={<ReportList />} />
        <Route path="/reports/:id" element={<ReportDetail />} />

        {/* 模块 05 权限 */}
        <Route
          path="/admin/users"
          element={
            <RequireAdmin>
              <Users />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/prompt-templates"
          element={
            <RequireAdmin>
              <AdminPromptTemplates />
            </RequireAdmin>
          }
        />
        <Route path="/profile" element={<Profile />} />

        {/* 模块 06 自动采集 */}
        <Route path="/collection/benchmark-accounts" element={<BenchmarkAccounts />} />
        <Route path="/collection/tasks" element={<CollectionTasks />} />

        {/* 模块 07 研究助手 */}
        <Route path="/research/tasks" element={<ResearchTasks />} />
        <Route path="/research/reports/:id" element={<ResearchReport />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
