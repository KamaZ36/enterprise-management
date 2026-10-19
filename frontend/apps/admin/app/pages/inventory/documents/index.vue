<template>
  <div class="page">
    <h1 class="page__title">Журнал склада</h1>
    <p class="page__subtitle">
      Поступления и списания. Нажмите на строку, чтобы открыть документ.
    </p>

    <div class="page__toolbar">
      <el-button
        v-if="canCreateDocument"
        type="primary"
        @click="openCreate"
      >
        Новое поступление
      </el-button>
      <el-button v-if="canCreateDocument" @click="openTransferCreate">
        Новое перемещение
      </el-button>
      <el-button v-if="canCreateDocument" @click="openWriteOffCreate">
        Новое списание
      </el-button>
      <el-button v-if="canCreateDocument" @click="openInventoryCountCreate">
        Новая инвентаризация
      </el-button>
      <el-input
        v-model="filter"
        placeholder="Поставщик, номер документа или причина"
        style="width: 320px"
        clearable
        @input="onFilter"
      />
      <el-select
        v-if="can('inventory.document.read')"
        v-model="locationId"
        placeholder="Все точки"
        clearable
        style="width: 260px"
        @change="reload"
      >
        <LocationOptions :locations="locations" />
      </el-select>
      <el-button :loading="pending" @click="reload">Обновить</el-button>
    </div>

    <el-tabs v-model="tab" @tab-change="reload">
      <el-tab-pane label="Поступления" name="receipts" />
      <el-tab-pane label="Списания" name="write-offs" />
      <el-tab-pane label="Перемещения" name="transfers" />
      <el-tab-pane label="Инвентаризации" name="inventory-counts" />
    </el-tabs>

    <el-alert
      v-if="notice"
      :title="notice"
      type="success"
      :closable="false"
      show-icon
      class="page__error"
    />
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-table
      v-if="tab === 'receipts'"
      v-loading="pending"
      :data="receipts"
      stripe
      border
      @row-click="openReceipt"
    >
      <el-table-column label="Дата" width="120">
        <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Подразделение" min-width="180">
        <template #default="{ row }">{{ locationName(row.org_unit_id) }}</template>
      </el-table-column>
      <el-table-column label="Поставщик" min-width="220">
        <template #default="{ row }">{{ row.supplier_name ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Документ" width="150">
        <template #default="{ row }">{{ row.supplier_document_number ?? "—" }}</template>
      </el-table-column>
      <el-table-column prop="line_count" label="Строк" width="90" align="right" />
      <el-table-column label="Сумма" width="150" align="right">
        <template #default="{ row }">{{ formatKopecks(row.total_kopecks) }}</template>
      </el-table-column>
      <el-table-column label="Статус" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'posted' ? 'success' : 'info'" effect="light">
            {{ row.status === "posted" ? "проведён" : "черновик" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column width="230" align="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'draft' && can('inventory.document.post')"
            text
            :disabled="busy"
            @click.stop="postReceipt(row as ReceiptListItem)"
          >
            Провести
          </el-button>
          <el-popconfirm
            v-if="row.status === 'draft' && canCreateDocument"
            title="Удалить черновик поступления?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteReceipt(row as ReceiptListItem)"
          >
            <template #reference>
              <el-button text type="danger" :disabled="busy" @click.stop>
                Удалить
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="Поступлений пока нет" />
      </template>
    </el-table>

    <el-table
      v-else-if="tab === 'write-offs'"
      v-loading="pending"
      :data="writeOffs"
      stripe
      border
      @row-click="openWriteOff"
    >
      <el-table-column label="Дата" width="120">
        <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Подразделение" min-width="180">
        <template #default="{ row }">{{ locationName(row.org_unit_id) }}</template>
      </el-table-column>
      <el-table-column label="Причина" min-width="220">
        <template #default="{ row }">{{ row.reason ?? "—" }}</template>
      </el-table-column>
      <el-table-column prop="line_count" label="Строк" width="90" align="right" />
      <el-table-column label="Статус" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'posted' ? 'success' : 'info'" effect="light">
            {{ row.status === "posted" ? "проведён" : "черновик" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column width="230" align="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'draft' && can('inventory.document.post')"
            text
            :disabled="busy"
            @click.stop="postWriteOff(row as WriteOffListItem)"
          >
            Провести
          </el-button>
          <el-popconfirm
            v-if="row.status === 'draft' && canCreateDocument"
            title="Удалить черновик списания?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteWriteOff(row as WriteOffListItem)"
          >
            <template #reference>
              <el-button text type="danger" :disabled="busy" @click.stop>
                Удалить
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="Списаний пока нет" />
      </template>
    </el-table>

    <el-table
      v-else-if="tab === 'inventory-counts'"
      v-loading="pending"
      :data="inventoryCounts"
      stripe
      border
      @row-click="openInventoryCount"
    >
      <el-table-column label="Дата" width="120">
        <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Подразделение" min-width="180">
        <template #default="{ row }">{{ locationName(row.org_unit_id) }}</template>
      </el-table-column>
      <el-table-column label="Комментарий" min-width="220">
        <template #default="{ row }">{{ row.comment ?? "—" }}</template>
      </el-table-column>
      <el-table-column prop="line_count" label="Строк" width="90" align="right" />
      <el-table-column label="Статус" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'posted' ? 'success' : 'info'" effect="light">
            {{ row.status === "posted" ? "проведён" : "черновик" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column width="230" align="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'draft' && can('inventory.document.post')"
            text
            :disabled="icPosting"
            @click.stop="postInventoryCount(row.id)"
          >
            Провести
          </el-button>
          <el-popconfirm
            v-if="row.status === 'draft' && canCreateDocument"
            title="Удалить черновик инвентаризации?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteInventoryCount(row.id)"
          >
            <template #reference>
              <el-button text type="danger" :disabled="busy" @click.stop>
                Удалить
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="Инвентаризаций пока нет" />
      </template>
    </el-table>

    <el-pagination
      v-if="tab !== 'transfers'"
      v-model:current-page="page"
      class="pager"
      layout="prev, pager, next, total"
      :page-size="PAGE_SIZE"
      :total="pagerTotal"
      :disabled="pending"
      @current-change="onPageChange"
    />


    <el-table
      v-if="tab === 'transfers'"
      v-loading="pending"
      :data="transfers"
      stripe
      border
      @row-click="openTransfer"
    >
      <el-table-column label="Дата" width="120">
        <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Откуда" min-width="180">
        <template #default="{ row }">{{ locationName(row.from_org_unit_id) }}</template>
      </el-table-column>
      <el-table-column label="Куда" min-width="180">
        <template #default="{ row }">{{ locationName(row.to_org_unit_id) }}</template>
      </el-table-column>
      <el-table-column prop="line_count" label="Строк" width="90" align="right" />
      <el-table-column label="Статус" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'posted' ? 'success' : 'info'" effect="light">
            {{ row.status === "posted" ? "проведён" : "черновик" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column width="150" align="right">
        <template #default="{ row }">
          <el-popconfirm
            v-if="row.status === 'draft' && canCreateDocument"
            title="Удалить черновик перемещения?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteTransfer(row as TransferListItem)"
          >
            <template #reference>
              <el-button text type="danger" :disabled="busy" @click.stop>
                Удалить
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="writeOffOpen"
      :title="editingWriteOffId ? 'Изменить списание' : 'Новое списание'"
      width="760"
    >
      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Подразделение">
            <el-select
              v-model="woForm.org_unit_id"
              style="width: 100%"
              :disabled="Boolean(editingWriteOffId)"
            >
              <LocationOptions :locations="locations" />
            </el-select>
          </el-form-item>
          <el-form-item label="Дата и время">
            <el-date-picker
              v-model="woForm.occurred_at"
              type="datetime"
              style="width: 100%"
            />
          </el-form-item>
        </div>

        <el-form-item label="Причина">
          <el-input v-model="woForm.reason" placeholder="Просрочка, брак, недостача" />
        </el-form-item>

        <div class="lines-head">
          <span>Строки документа</span>
          <el-button size="small" @click="addWriteOffLine">Добавить строку</el-button>
        </div>

        <div class="line line--head line--write-off">
          <span class="line__name">Номенклатура</span>
          <span class="line__qty">Количество</span>
          <span class="line__lot">Партия</span>
          <span class="line__action" />
        </div>

        <div v-for="(line, index) in woLines" :key="index" class="line line--write-off">
          <el-select
            v-model="line.nomenclature_id"
            filterable
            remote
            placeholder="Начните вводить название или артикул"
            :remote-method="(query: string) => searchNomenclature(line, query)"
            class="line__name"
          >
            <el-option
              v-for="option in line.options"
              :key="option.id"
              :label="`${option.name} · ${option.sku}`"
              :value="option.id"
            />
          </el-select>

          <el-input v-model="line.quantity" class="line__qty" placeholder="например 2,5" />
          <el-input v-model="line.lot_code" class="line__lot" placeholder="если нужна" />
          <el-button
            text
            type="danger"
            :disabled="woLines.length === 1"
            @click="removeWriteOffLine(index)"
          >
            Убрать
          </el-button>
        </div>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="Цены в списании нет"
          description="Себестоимость определится при проведении по средней в подразделении."
        />

        <el-alert v-if="woError" :title="woError" type="error" :closable="false" show-icon />
      </el-form>

      <template #footer>
        <el-button @click="writeOffOpen = false">Отмена</el-button>
        <el-button :loading="woSaving" :disabled="!woCanSubmit" @click="createWriteOff(false)">
          {{ editingWriteOffId ? "Сохранить" : "Сохранить черновик" }}
        </el-button>
        <el-button
          v-if="!editingWriteOffId"
          type="primary"
          :loading="woSaving"
          :disabled="!woCanSubmit"
          @click="createWriteOff(true)"
        >
          Сохранить и провести
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="createOpen"
      :title="editingReceiptId ? 'Изменить поступление' : 'Новое поступление'"
      width="900"
    >
      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Подразделение">
            <el-select
              v-model="form.org_unit_id"
              style="width: 100%"
              :disabled="Boolean(editingReceiptId)"
            >
              <LocationOptions :locations="locations" />
            </el-select>
          </el-form-item>
          <el-form-item label="Дата и время">
            <el-date-picker
              v-model="form.occurred_at"
              type="datetime"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="Поставщик">
            <el-input v-model="form.supplier_name" placeholder="Мясокомбинат" />
          </el-form-item>
          <el-form-item label="Номер документа поставщика">
            <el-input v-model="form.supplier_document_number" placeholder="УПД-1042" />
          </el-form-item>
        </div>

        <div class="lines-head">
          <span>Строки документа</span>
          <el-button size="small" @click="addLine">Добавить строку</el-button>
        </div>

        <div class="line line--head">
          <span class="line__name">Номенклатура</span>
          <span class="line__qty">Количество</span>
          <span class="line__qty">Цена, ₽</span>
          <span class="line__lot">Партия</span>
          <span class="line__date">Годен до</span>
          <span class="line__action" />
        </div>

        <div v-for="(line, index) in lines" :key="index" class="line">
          <el-select
            v-model="line.nomenclature_id"
            filterable
            remote
            placeholder="Начните вводить название или артикул"
            :remote-method="(query: string) => searchNomenclature(line, query)"
            class="line__name"
          >
            <el-option
              v-for="option in line.options"
              :key="option.id"
              :label="`${option.name} · ${option.sku}`"
              :value="option.id"
            />
          </el-select>

          <el-input v-model="line.quantity" class="line__qty" placeholder="например 12,5" />
          <el-input v-model="line.unit_cost" class="line__qty" placeholder="например 450,50" />
          <el-input v-model="line.lot_code" class="line__lot" placeholder="Партия" />
          <el-date-picker
            v-model="line.expires_at"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Годен до"
            class="line__date"
          />
          <el-button text type="danger" :disabled="lines.length === 1" @click="removeLine(index)">
            Убрать
          </el-button>
        </div>

        <el-form-item label="Комментарий">
          <el-input v-model="form.comment" />
        </el-form-item>

        <el-alert v-if="createError" :title="createError" type="error" :closable="false" show-icon />
      </el-form>

      <template #footer>
        <el-button @click="createOpen = false">Отмена</el-button>
        <el-button :loading="saving" :disabled="!canSubmit" @click="createReceipt(false)">
          {{ editingReceiptId ? "Сохранить" : "Сохранить черновик" }}
        </el-button>
        <el-button
          v-if="!editingReceiptId"
          type="primary"
          :loading="saving"
          :disabled="!canSubmit"
          @click="createReceipt(true)"
        >
          Сохранить и провести
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="transferOpen" title="Новое перемещение" width="820">
      <el-alert
        v-if="trError"
        :title="trError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Откуда">
            <el-select v-model="trForm.from_org_unit_id" style="width: 100%">
              <LocationOptions :locations="locations" />
            </el-select>
          </el-form-item>
          <el-form-item label="Куда">
            <el-select v-model="trForm.to_org_unit_id" style="width: 100%">
              <LocationOptions :locations="locations" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="Дата и время">
          <el-date-picker v-model="trForm.occurred_at" type="datetime" style="width: 100%" />
        </el-form-item>

        <el-form-item label="Комментарий">
          <el-input v-model="trForm.comment" placeholder="Необязательно" />
        </el-form-item>

        <div class="lines-head">
          <span>Строки документа</span>
          <el-button size="small" @click="addTransferLine">Добавить строку</el-button>
        </div>

        <div class="line line--head line--write-off">
          <span class="line__name">Номенклатура</span>
          <span class="line__qty">Количество</span>
          <span class="line__lot">Партия</span>
          <span class="line__action" />
        </div>

        <div v-for="(line, index) in trLines" :key="index" class="line line--write-off">
          <el-select
            v-model="line.nomenclature_id"
            filterable
            remote
            placeholder="Начните вводить название или артикул"
            :remote-method="(query: string) => searchNomenclature(line, query)"
            class="line__name"
          >
            <el-option
              v-for="option in line.options"
              :key="option.id"
              :label="option.sku ? `${option.name} · ${option.sku}` : option.name"
              :value="option.id"
            />
          </el-select>

          <el-input v-model="line.quantity" class="line__qty" placeholder="например 2,5" />
          <el-input v-model="line.lot_code" class="line__lot" placeholder="если нужна" />
          <el-button
            text
            type="danger"
            :disabled="trLines.length === 1"
            @click="removeTransferLine(index)"
          >
            Убрать
          </el-button>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="transferOpen = false">Отмена</el-button>
        <el-button :loading="trSaving" :disabled="!trCanSubmit" @click="createTransfer(false)">
          Сохранить черновик
        </el-button>
        <el-button
          type="primary"
          :loading="trSaving"
          :disabled="!trCanSubmit"
          @click="createTransfer(true)"
        >
          Сохранить и провести
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="transferDrawerOpen" :title="transferDrawerTitle" size="600px">
      <template v-if="transferDetail">
        <el-alert
          v-if="trDetailError"
          :title="trDetailError"
          type="error"
          :closable="false"
          show-icon
          class="page__error"
        />

        <el-descriptions :column="1" border>
          <el-descriptions-item label="Откуда">
            {{ locationName(transferDetail.from_org_unit_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="Куда">
            {{ locationName(transferDetail.to_org_unit_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="Дата">
            {{ formatDate(transferDetail.occurred_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Статус">
            <el-tag
              :type="transferDetail.status === 'posted' ? 'success' : 'info'"
              effect="light"
            >
              {{ transferDetail.status === "posted" ? "проведён" : "черновик" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="transferDetail.comment" label="Комментарий">
            {{ transferDetail.comment }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table :data="transferDetail.lines" border class="lines">
          <el-table-column prop="nomenclature_name" label="Номенклатура" min-width="200" />
          <el-table-column prop="quantity" label="Количество" width="130" align="right" />
          <el-table-column prop="lot_code" label="Партия" width="130" />
        </el-table>

        <div
          v-if="transferDetail.status !== 'posted'"
          style="display: flex; gap: 8px; margin-top: 16px"
        >
          <el-button @click="openTransferEdit">Редактировать</el-button>
          <el-button type="primary" :loading="trPosting" @click="postTransfer">
            Провести
          </el-button>
          <el-popconfirm
            v-if="canCreateDocument"
            title="Удалить черновик перемещения?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteTransfer(transferDetail)"
          >
            <template #reference>
              <el-button type="danger" text :disabled="busy">Удалить</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>
    </el-drawer>

    <el-drawer v-model="drawerOpen" :title="drawerTitle" size="640px">
      <template v-if="receiptDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Дата">
            {{ formatDate(receiptDetail.occurred_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Подразделение">
            {{ locationName(receiptDetail.org_unit_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="Поставщик">
            {{ receiptDetail.supplier_name ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Документ поставщика">
            {{ receiptDetail.supplier_document_number ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Проведён">
            {{ receiptDetail.posted_at ? formatDate(receiptDetail.posted_at) : "нет" }}
          </el-descriptions-item>
          <el-descriptions-item label="Комментарий">
            {{ receiptDetail.comment ?? "—" }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table :data="receiptDetail.lines" border class="lines">
          <el-table-column prop="nomenclature_name" label="Номенклатура" min-width="200" />
          <el-table-column label="Количество" width="130" align="right">
            <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="Цена" width="120" align="right">
            <template #default="{ row }">{{ formatQuantity(row.unit_cost, 2) }}</template>
          </el-table-column>
          <el-table-column label="Сумма" width="140" align="right">
            <template #default="{ row }">{{ formatKopecks(row.total_kopecks) }}</template>
          </el-table-column>
          <el-table-column label="Партия" width="140">
            <template #default="{ row }">
              <span>{{ row.lot_code ?? "—" }}</span>
              <div v-if="row.expires_at" class="muted hint">
                до {{ formatDate(row.expires_at) }}
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div
          v-if="receiptDetail.status !== 'posted'"
          style="display: flex; gap: 8px; margin-top: 16px"
        >
          <el-button @click="openReceiptEdit">Редактировать</el-button>
          <el-button
            type="primary"
            :loading="busy"
            @click="postReceipt(receiptDetail)"
          >
            Провести
          </el-button>
          <el-popconfirm
            v-if="canCreateDocument"
            title="Удалить черновик поступления?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteReceipt(receiptDetail)"
          >
            <template #reference>
              <el-button type="danger" text :disabled="busy">Удалить</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>

      <template v-else-if="writeOffDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Дата">
            {{ formatDate(writeOffDetail.occurred_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Подразделение">
            {{ locationName(writeOffDetail.org_unit_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="Причина">
            {{ writeOffDetail.reason ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Проведён">
            {{ writeOffDetail.posted_at ? formatDate(writeOffDetail.posted_at) : "нет" }}
          </el-descriptions-item>
          <el-descriptions-item label="Комментарий" :span="2">
            {{ writeOffDetail.comment ?? "—" }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table :data="writeOffDetail.lines" border class="lines">
          <el-table-column prop="nomenclature_name" label="Номенклатура" min-width="220" />
          <el-table-column label="Количество" width="140" align="right">
            <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="Партия" width="150">
            <template #default="{ row }">{{ row.lot_code ?? "—" }}</template>
          </el-table-column>
        </el-table>

        <el-alert
          class="lines"
          type="info"
          :closable="false"
          show-icon
          title="Себестоимость списания"
          description="В документе цены нет: стоимость определяется при проведении по средней. Показывать её будет карточка движений."
        />

        <div
          v-if="writeOffDetail.status !== 'posted'"
          style="display: flex; gap: 8px; margin-top: 16px"
        >
          <el-button @click="openWriteOffEdit">Редактировать</el-button>
          <el-button
            type="primary"
            :loading="busy"
            @click="postWriteOff(writeOffDetail)"
          >
            Провести
          </el-button>
          <el-popconfirm
            v-if="canCreateDocument"
            title="Удалить черновик списания?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteWriteOff(writeOffDetail)"
          >
            <template #reference>
              <el-button type="danger" text :disabled="busy">Удалить</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="icOpen"
      :title="icEditingId ? 'Изменить инвентаризацию' : 'Новая инвентаризация'"
      width="860"
    >
      <el-alert
        v-if="icError"
        :title="icError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Подразделение">
            <el-select
              v-model="icForm.org_unit_id"
              style="width: 100%"
              :disabled="Boolean(icEditingId)"
            >
              <LocationOptions :locations="locations" />
            </el-select>
          </el-form-item>
          <el-form-item label="Дата и время">
            <el-date-picker
              v-model="icForm.occurred_at"
              type="datetime"
              style="width: 100%"
            />
          </el-form-item>
        </div>

        <el-form-item label="Комментарий">
          <el-input v-model="icForm.comment" placeholder="Необязательно" />
        </el-form-item>

        <div class="lines-head">
          <span>Строки документа</span>
          <el-button size="small" @click="addInventoryCountLine">Добавить строку</el-button>
        </div>

        <div class="line line--head line--count">
          <span class="line__name">Номенклатура</span>
          <span class="line__qty line__qty--book">Учёт</span>
          <span class="line__qty">Факт</span>
          <span class="line__lot">Партия</span>
          <span class="line__action" />
        </div>

        <div v-for="(line, index) in icLines" :key="index" class="line line--count">
          <el-select
            v-model="line.nomenclature_id"
            filterable
            remote
            placeholder="Начните вводить название или артикул"
            :remote-method="(query: string) => searchNomenclature(line, query)"
            class="line__name"
          >
            <el-option
              v-for="option in line.options"
              :key="option.id"
              :label="option.sku ? `${option.name} · ${option.sku}` : option.name"
              :value="option.id"
            />
          </el-select>

          <span class="line__qty line__qty--book">{{ bookQuantity(line.nomenclature_id) }}</span>
          <el-input
            v-model="line.counted_quantity"
            class="line__qty"
            placeholder="например 12,5"
          />
          <el-input v-model="line.lot_code" class="line__lot" placeholder="если нужна" />
          <el-button
            text
            type="danger"
            :disabled="icLines.length === 1"
            @click="removeInventoryCountLine(index)"
          >
            Убрать
          </el-button>
        </div>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="Разница считается при проведении"
          description="Фактическое количество сравнивается с учётным остатком в момент проведения: излишек приходуется по средней себестоимости, недостача списывается по FEFO или указанной партии."
        />
      </el-form>

      <template #footer>
        <el-button @click="icOpen = false">Отмена</el-button>
        <el-button :loading="icSaving" :disabled="!icCanSubmit" @click="saveInventoryCount(false)">
          {{ icEditingId ? "Сохранить" : "Сохранить черновик" }}
        </el-button>
        <el-button
          v-if="!icEditingId"
          type="primary"
          :loading="icSaving"
          :disabled="!icCanSubmit"
          @click="saveInventoryCount(true)"
        >
          Сохранить и провести
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="icDrawerOpen" :title="icDrawerTitle" size="640px">
      <template v-if="inventoryCountDetail">
        <el-alert
          v-if="icDetailError"
          :title="icDetailError"
          type="error"
          :closable="false"
          show-icon
          class="page__error"
        />

        <el-descriptions :column="2" border>
          <el-descriptions-item label="Дата">
            {{ formatDate(inventoryCountDetail.occurred_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Подразделение">
            {{ locationName(inventoryCountDetail.org_unit_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="Статус">
            <el-tag
              :type="inventoryCountDetail.status === 'posted' ? 'success' : 'info'"
              effect="light"
            >
              {{ inventoryCountDetail.status === "posted" ? "проведён" : "черновик" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Проведён">
            {{ inventoryCountDetail.posted_at ? formatDate(inventoryCountDetail.posted_at) : "нет" }}
          </el-descriptions-item>
          <el-descriptions-item v-if="inventoryCountDetail.comment" label="Комментарий" :span="2">
            {{ inventoryCountDetail.comment }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table :data="inventoryCountDetail.lines" border class="lines">
          <el-table-column prop="nomenclature_name" label="Номенклатура" min-width="200" />
          <el-table-column label="Факт" width="130" align="right">
            <template #default="{ row }">{{ formatQuantity(row.counted_quantity) }}</template>
          </el-table-column>
          <el-table-column label="Партия" width="140">
            <template #default="{ row }">{{ row.lot_code ?? "—" }}</template>
          </el-table-column>
        </el-table>

        <div
          v-if="inventoryCountDetail.status !== 'posted'"
          style="display: flex; gap: 8px; margin-top: 16px"
        >
          <el-button @click="openInventoryCountEdit">Редактировать</el-button>
          <el-button
            type="primary"
            :loading="icPosting"
            @click="postInventoryCount(inventoryCountDetail.id)"
          >
            Провести
          </el-button>
          <el-popconfirm
            v-if="canCreateDocument"
            title="Удалить черновик инвентаризации?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="deleteInventoryCount(inventoryCountDetail.id)"
          >
            <template #reference>
              <el-button type="danger" text :disabled="busy">Удалить</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.documentsOpen });
import { formatKopecks, formatQuantity } from "@md/money";
import type { components } from "@md/api-client";
import { locationDisplay } from "~/utils/locations";

type ReceiptListItem = components["schemas"]["ReceiptListItemSchema"];
type ReceiptDetail = components["schemas"]["ReceiptDetailSchema"];
type WriteOffListItem = components["schemas"]["WriteOffListItemSchema"];
type WriteOffDetail = components["schemas"]["WriteOffDetailSchema"];
type InventoryCountListItem =
  components["schemas"]["InventoryCountListItemSchema"];
type InventoryCountDetail = components["schemas"]["InventoryCountDetailSchema"];
type TransferListItem = components["schemas"]["TransferListItemSchema"];
type Location = components["schemas"]["LocationSchema"];

const PAGE_SIZE = 20;

const api = useApi();
const { can } = useCurrentUser();

const canCreateDocument = computed(() => canAll(CAN.documentsCreate));

const tab = ref<"receipts" | "write-offs" | "transfers" | "inventory-counts">(
  "receipts",
);
const transfers = ref<components["schemas"]["TransferListItemSchema"][]>([]);
const receipts = ref<ReceiptListItem[]>([]);
const writeOffs = ref<WriteOffListItem[]>([]);
const inventoryCounts = ref<InventoryCountListItem[]>([]);
const receiptsTotal = ref(0);
const writeOffsTotal = ref(0);
const inventoryCountsTotal = ref(0);
const locations = ref<Location[]>([]);
const locationId = ref<string | null>(null);
const page = ref(1);
const pending = ref(false);
const error = ref("");
const notice = ref("");
const filter = ref("");

const drawerOpen = ref(false);
const createOpen = ref(false);
const saving = ref(false);
const busy = ref(false);
const createError = ref("");
const editingReceiptId = ref<string | null>(null);

type NomenclatureOption = { id: string; name: string; sku: string };
type DraftLine = {
  nomenclature_id: string;
  options: NomenclatureOption[];
  quantity: string;
  unit_cost: string;
  lot_code: string;
  expires_at: string;
};

function emptyLine(): DraftLine {
  return {
    nomenclature_id: "",
    options: [],
    quantity: "",
    unit_cost: "",
    lot_code: "",
    expires_at: "",
  };
}

function isCompleteLine(line: DraftLine): boolean {
  return (
    Boolean(line.nomenclature_id) &&
    Number(line.quantity) > 0 &&
    line.unit_cost !== "" &&
    Number(line.unit_cost) >= 0
  );
}

const form = reactive({
  org_unit_id: "",
  occurred_at: new Date(),
  supplier_name: "",
  supplier_document_number: "",
  comment: "",
});
const lines = ref<DraftLine[]>([emptyLine()]);

type WriteOffLine = {
  nomenclature_id: string;
  options: NomenclatureOption[];
  quantity: string;
  lot_code: string;
};

function emptyWriteOffLine(): WriteOffLine {
  return { nomenclature_id: "", options: [], quantity: "", lot_code: "" };
}

const writeOffOpen = ref(false);
const woSaving = ref(false);
const woError = ref("");
const editingWriteOffId = ref<string | null>(null);
const woForm = reactive({
  org_unit_id: "",
  occurred_at: new Date(),
  reason: "",
  comment: "",
});
const woLines = ref<WriteOffLine[]>([emptyWriteOffLine()]);

function isCompleteWriteOffLine(line: WriteOffLine): boolean {
  return Boolean(line.nomenclature_id) && Number(line.quantity) > 0;
}

const woCanSubmit = computed(
  () => Boolean(woForm.org_unit_id) && woLines.value.some(isCompleteWriteOffLine),
);

const canSubmit = computed(
  () => Boolean(form.org_unit_id) && lines.value.some(isCompleteLine),
);
const receiptDetail = ref<ReceiptDetail | null>(null);
const writeOffDetail = ref<WriteOffDetail | null>(null);

const drawerTitle = computed(() => {
  if (receiptDetail.value) {
    return `Поступление от ${formatDate(receiptDetail.value.occurred_at)}`;
  }
  if (writeOffDetail.value) {
    return `Списание от ${formatDate(writeOffDetail.value.occurred_at)}`;
  }

  return "Документ";
});

function locationName(id: string): string {
  return locationDisplay(
    locations.value.find((location) => location.id === id),
  );
}

function reasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав смотреть документы склада";
  }
  if (status === 404) {
    return "Документ не найден";
  }

  return `${fallback}: ${status}`;
}

async function loadLocations(): Promise<void> {
  if (!can("inventory.document.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/locations", {});
  if (response.ok && data) {
    locations.value = data;
  }
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  const query = {
    org_unit_id: locationId.value ?? undefined,
    limit: PAGE_SIZE,
    offset: (page.value - 1) * PAGE_SIZE,
    search: filter.value.trim() || undefined,
  };

  try {
    if (tab.value === "receipts") {
      const { data, response } = await api.GET("/api/inventory/receipts", {
        params: { query },
      });
      if (!response.ok || !data) {
        throw new Error(reasonOf(response.status, "Не удалось загрузить поступления"));
      }

      receipts.value = data.items;
      receiptsTotal.value = data.total;
    } else {
      const { data, response } = await api.GET("/api/inventory/write-offs", {
        params: { query },
      });
      if (!response.ok || !data) {
        throw new Error(reasonOf(response.status, "Не удалось загрузить списания"));
      }

      writeOffs.value = data.items;
      writeOffsTotal.value = data.total;
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

async function loadInventoryCounts(): Promise<void> {
  pending.value = true;
  error.value = "";

  const { data, response } = await api.GET("/api/inventory/inventory-counts", {
    params: {
      query: {
        org_unit_id: locationId.value ?? undefined,
        limit: PAGE_SIZE,
        offset: (page.value - 1) * PAGE_SIZE,
        search: filter.value.trim() || undefined,
      },
    },
  });

  if (response.ok && data) {
    inventoryCounts.value = data.items;
    inventoryCountsTotal.value = data.total;
  } else {
    error.value = reasonOf(
      response.status,
      "Не удалось загрузить инвентаризации",
    );
  }

  pending.value = false;
}

const pagerTotal = computed(() => {
  if (tab.value === "receipts") {
    return receiptsTotal.value;
  }
  if (tab.value === "write-offs") {
    return writeOffsTotal.value;
  }

  return inventoryCountsTotal.value;
});

async function refresh(): Promise<void> {
  if (tab.value === "transfers") {
    await loadTransfers();
    return;
  }
  if (tab.value === "inventory-counts") {
    await loadInventoryCounts();
    return;
  }

  await load();
}

async function reload(): Promise<void> {
  page.value = 1;
  await refresh();
}

async function onPageChange(): Promise<void> {
  if (tab.value === "inventory-counts") {
    await loadInventoryCounts();
    return;
  }

  await load();
}

async function openReceipt(row: { id: string }): Promise<void> {
  receiptDetail.value = null;
  writeOffDetail.value = null;

  const { data, response } = await api.GET("/api/inventory/receipts/{receipt_id}", {
    params: { path: { receipt_id: row.id } },
  });

  if (response.ok && data) {
    receiptDetail.value = data;
    drawerOpen.value = true;
  } else {
    error.value = reasonOf(response.status, "Не удалось открыть документ");
  }
}

async function openWriteOff(row: { id: string }): Promise<void> {
  receiptDetail.value = null;
  writeOffDetail.value = null;

  const { data, response } = await api.GET("/api/inventory/write-offs/{write_off_id}", {
    params: { path: { write_off_id: row.id } },
  });

  if (response.ok && data) {
    writeOffDetail.value = data;
    drawerOpen.value = true;
  } else {
    error.value = reasonOf(response.status, "Не удалось открыть документ");
  }
}

function serverMessage(error: unknown, fallback: string): string {
  const payload = error as { message?: string } | undefined;

  return payload?.message ?? fallback;
}


function openCreate(): void {
  createError.value = "";
  notice.value = "";
  editingReceiptId.value = null;
  form.org_unit_id = locations.value[0]?.id ?? "";
  form.occurred_at = new Date();
  form.supplier_name = "";
  form.supplier_document_number = "";
  form.comment = "";
  lines.value = [emptyLine()];
  createOpen.value = true;
}


function openReceiptEdit(): void {
  const detail = receiptDetail.value;

  if (!detail) {
    return;
  }

  createError.value = "";
  notice.value = "";
  editingReceiptId.value = detail.id;
  form.org_unit_id = detail.org_unit_id;
  form.occurred_at = new Date(detail.occurred_at);
  form.supplier_name = detail.supplier_name ?? "";
  form.supplier_document_number = detail.supplier_document_number ?? "";
  form.comment = detail.comment ?? "";
  lines.value = detail.lines.map((line) => ({
    nomenclature_id: line.nomenclature_id,
    quantity: String(line.quantity),
    unit_cost: String(line.unit_cost),
    lot_code: line.lot_code ?? "",
    expires_at: line.expires_at ?? "",
    options: [
      {
        id: line.nomenclature_id,
        name: line.nomenclature_name ?? line.nomenclature_id,
        sku: "",
      },
    ],
  }));
  drawerOpen.value = false;
  createOpen.value = true;
}


function addLine(): void {
  lines.value = [...lines.value, emptyLine()];
}


function removeLine(index: number): void {
  lines.value = lines.value.filter((_, position) => position !== index);
}


async function searchNomenclature(
  line: { options: NomenclatureOption[] },
  query: string,
): Promise<void> {
  const { data, response } = await api.GET("/api/catalog/nomenclatures", {
    params: { query: { search: query || undefined, limit: 20 } },
  });

  if (response.ok && data) {
    line.options = data.items;
  }
}


async function createReceipt(postAfterCreate: boolean): Promise<void> {
  saving.value = true;
  createError.value = "";
  notice.value = "";

  try {
    const body = {
      occurred_at: form.occurred_at.toISOString(),
      supplier_name: form.supplier_name.trim() || null,
      supplier_document_number: form.supplier_document_number.trim() || null,
      comment: form.comment.trim() || null,
      lines: lines.value
        .filter(isCompleteLine)
        .map((line) => ({
          nomenclature_id: line.nomenclature_id,
          quantity: line.quantity,
          unit_cost: line.unit_cost,
          lot_code: line.lot_code.trim() || null,
          expires_at: line.expires_at || null,
        })),
    };

    if (editingReceiptId.value) {
      const editedId = editingReceiptId.value;
      const updated = await api.PATCH("/api/inventory/receipts/{receipt_id}", {
        params: { path: { receipt_id: editedId } },
        body,
      });

      if (!updated.response.ok) {
        throw new Error(
          serverMessage(updated.error, `Не удалось сохранить: ${updated.response.status}`),
        );
      }

      createOpen.value = false;
      editingReceiptId.value = null;
      notice.value = "Изменения сохранены";
      await openReceipt({ id: editedId });
      await load();
      return;
    }

    const created = await api.POST("/api/inventory/receipts", {
      body: { org_unit_id: form.org_unit_id, ...body },
    });

    if (!created.response.ok || !created.data) {
      throw new Error(serverMessage(created.error, `Не удалось сохранить: ${created.response.status}`));
    }

    const receiptId = (created.data as unknown as { receipt_id: string }).receipt_id;

    if (postAfterCreate) {
      const posted = await api.POST("/api/inventory/receipts/{receipt_id}/post", {
        params: { path: { receipt_id: receiptId } },
      });

      if (!posted.response.ok) {
        createError.value = `Черновик создан, но не проведён: ${serverMessage(posted.error, String(posted.response.status))}`;
        await load();
        return;
      }

      notice.value = "Поступление проведено";
      tab.value = "receipts";
    } else {
      notice.value = "Черновик поступления сохранён";
    }

    createOpen.value = false;
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}


function openWriteOffCreate(): void {
  woError.value = "";
  notice.value = "";
  editingWriteOffId.value = null;
  woForm.org_unit_id = locations.value[0]?.id ?? "";
  woForm.occurred_at = new Date();
  woForm.reason = "";
  woForm.comment = "";
  woLines.value = [emptyWriteOffLine()];
  writeOffOpen.value = true;
}


function openWriteOffEdit(): void {
  const detail = writeOffDetail.value;

  if (!detail) {
    return;
  }

  woError.value = "";
  notice.value = "";
  editingWriteOffId.value = detail.id;
  woForm.org_unit_id = detail.org_unit_id;
  woForm.occurred_at = new Date(detail.occurred_at);
  woForm.reason = detail.reason ?? "";
  woForm.comment = detail.comment ?? "";
  woLines.value = detail.lines.map((line) => ({
    nomenclature_id: line.nomenclature_id,
    quantity: String(line.quantity),
    lot_code: line.lot_code ?? "",
    options: [
      {
        id: line.nomenclature_id,
        name: line.nomenclature_name ?? line.nomenclature_id,
        sku: "",
      },
    ],
  }));
  drawerOpen.value = false;
  writeOffOpen.value = true;
}


function addWriteOffLine(): void {
  woLines.value = [...woLines.value, emptyWriteOffLine()];
}


function removeWriteOffLine(index: number): void {
  woLines.value = woLines.value.filter((_, position) => position !== index);
}


async function createWriteOff(postAfterCreate: boolean): Promise<void> {
  woSaving.value = true;
  woError.value = "";
  notice.value = "";

  try {
    const body = {
      occurred_at: woForm.occurred_at.toISOString(),
      reason: woForm.reason.trim() || null,
      comment: woForm.comment.trim() || null,
      lines: woLines.value
        .filter(isCompleteWriteOffLine)
        .map((line) => ({
          nomenclature_id: line.nomenclature_id,
          quantity: line.quantity,
          lot_code: line.lot_code.trim() || null,
        })),
    };

    if (editingWriteOffId.value) {
      const editedId = editingWriteOffId.value;
      const updated = await api.PATCH("/api/inventory/write-offs/{write_off_id}", {
        params: { path: { write_off_id: editedId } },
        body,
      });

      if (!updated.response.ok) {
        throw new Error(
          serverMessage(updated.error, `Не удалось сохранить: ${updated.response.status}`),
        );
      }

      writeOffOpen.value = false;
      editingWriteOffId.value = null;
      notice.value = "Изменения сохранены";
      await openWriteOff({ id: editedId });
      await load();
      return;
    }

    const created = await api.POST("/api/inventory/write-offs", {
      body: { org_unit_id: woForm.org_unit_id, ...body },
    });

    if (!created.response.ok || !created.data) {
      throw new Error(serverMessage(created.error, `Не удалось сохранить: ${created.response.status}`));
    }

    const writeOffId = (created.data as unknown as { write_off_id: string }).write_off_id;

    if (postAfterCreate) {
      const posted = await api.POST("/api/inventory/write-offs/{write_off_id}/post", {
        params: { path: { write_off_id: writeOffId } },
      });

      if (!posted.response.ok) {
        woError.value = `Черновик создан, но не проведён: ${serverMessage(posted.error, String(posted.response.status))}`;
        tab.value = "write-offs";
        await load();
        return;
      }

      notice.value = "Списание проведено";
    } else {
      notice.value = "Черновик списания сохранён";
    }

    writeOffOpen.value = false;
    tab.value = "write-offs";
    await load();
  } catch (cause) {
    woError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    woSaving.value = false;
  }
}


async function postWriteOff(row: { id: string }): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/inventory/write-offs/{write_off_id}/post",
      { params: { path: { write_off_id: row.id } } },
    );

    if (!response.ok) {
      throw new Error(serverMessage(failure, `Не удалось провести: ${response.status}`));
    }

    notice.value = "Списание проведено";
    if (drawerOpen.value && writeOffDetail.value?.id === row.id) {
      await openWriteOff({ id: row.id });
    }
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка проведения";
  } finally {
    busy.value = false;
  }
}


async function postReceipt(row: { id: string }): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/inventory/receipts/{receipt_id}/post",
      { params: { path: { receipt_id: row.id } } },
    );

    if (!response.ok) {
      throw new Error(serverMessage(failure, `Не удалось провести: ${response.status}`));
    }

    notice.value = "Поступление проведено";
    if (drawerOpen.value && receiptDetail.value?.id === row.id) {
      await openReceipt({ id: row.id });
    }
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка проведения";
  } finally {
    busy.value = false;
  }
}


let filterTimer: ReturnType<typeof setTimeout> | undefined;

function onFilter(): void {
  if (filterTimer) {
    clearTimeout(filterTimer);
  }

  filterTimer = setTimeout(() => {
    page.value = 1;
    void refresh();
  }, 300);
}


onMounted(async () => {
  await loadLocations();
  await load();
});

async function loadTransfers(): Promise<void> {
  pending.value = true;

  const { data, response } = await api.GET("/api/inventory/transfers", {
    params: { query: { limit: 50 } },
  });

  if (response.ok && data) {
    transfers.value = data.items;
  }

  pending.value = false;
}

type TransferLine = {
  nomenclature_id: string;
  quantity: string;
  lot_code: string;
  options: NomenclatureOption[];
};

function emptyTransferLine(): TransferLine {
  return { nomenclature_id: "", quantity: "", lot_code: "", options: [] };
}

const transferOpen = ref(false);
const trSaving = ref(false);
const trError = ref("");
const trForm = reactive({
  from_org_unit_id: "",
  to_org_unit_id: "",
  occurred_at: new Date(),
  comment: "",
});
const trLines = ref<TransferLine[]>([emptyTransferLine()]);

function isCompleteTransferLine(line: TransferLine): boolean {
  return Boolean(line.nomenclature_id) && Number(line.quantity) > 0;
}

const trCanSubmit = computed(
  () =>
    Boolean(trForm.from_org_unit_id) &&
    Boolean(trForm.to_org_unit_id) &&
    trForm.from_org_unit_id !== trForm.to_org_unit_id &&
    trLines.value.some(isCompleteTransferLine),
);

function openTransferCreate(): void {
  trEditingId.value = null;
  trError.value = "";
  notice.value = "";
  trForm.from_org_unit_id = locations.value[0]?.id ?? "";
  trForm.to_org_unit_id = locations.value[1]?.id ?? "";
  trForm.occurred_at = new Date();
  trForm.comment = "";
  trLines.value = [emptyTransferLine()];
  transferOpen.value = true;
}

function addTransferLine(): void {
  trLines.value = [...trLines.value, emptyTransferLine()];
}

function removeTransferLine(index: number): void {
  trLines.value = trLines.value.filter((_, position) => position !== index);
}

async function createTransfer(postAfterCreate: boolean): Promise<void> {
  trSaving.value = true;
  trError.value = "";
  notice.value = "";

  try {
    if (trForm.from_org_unit_id === trForm.to_org_unit_id) {
      trError.value = "Подразделение-отправитель и подразделение-получатель должны различаться";
      return;
    }

    if (trEditingId.value) {
      const updated = await api.PATCH("/api/inventory/transfers/{transfer_id}", {
        params: { path: { transfer_id: trEditingId.value } },
        body: {
          occurred_at: trForm.occurred_at.toISOString(),
          comment: trForm.comment.trim() || null,
          lines: trLines.value.filter(isCompleteTransferLine).map((line) => ({
            nomenclature_id: line.nomenclature_id,
            quantity: line.quantity,
            lot_code: line.lot_code.trim() || null,
          })),
        },
      });

      if (!updated.response.ok) {
        trError.value = "Не удалось сохранить изменения";
        return;
      }

      const editedId = trEditingId.value;
      transferOpen.value = false;
      trEditingId.value = null;
      notice.value = "Изменения сохранены";
      await openTransfer({ id: editedId });
      await reload();
      return;
    }

    const created = await api.POST("/api/inventory/transfers", {
      body: {
        from_org_unit_id: trForm.from_org_unit_id,
        to_org_unit_id: trForm.to_org_unit_id,
        occurred_at: trForm.occurred_at.toISOString(),
        comment: trForm.comment.trim() || null,
        lines: trLines.value.filter(isCompleteTransferLine).map((line) => ({
          nomenclature_id: line.nomenclature_id,
          quantity: line.quantity,
          lot_code: line.lot_code.trim() || null,
        })),
      },
    });

    if (!created.response.ok || !created.data) {
      trError.value = "Не удалось создать перемещение";
      return;
    }

    if (postAfterCreate) {
      const transferId = (created.data as { transfer_id: string }).transfer_id;
      const posted = await api.POST("/api/inventory/transfers/{transfer_id}/post", {
        params: { path: { transfer_id: transferId } },
      });

      if (!posted.response.ok) {
        trError.value = "Не удалось провести перемещение";
        return;
      }
    }

    transferOpen.value = false;
    notice.value = postAfterCreate
      ? "Перемещение проведено"
      : "Черновик перемещения сохранён";
    tab.value = "transfers";
    await reload();
  } finally {
    trSaving.value = false;
  }
}

type TransferDetail = components["schemas"]["TransferDetailSchema"];

const transferDrawerOpen = ref(false);
const transferDetail = ref<TransferDetail | null>(null);
const trDetailError = ref("");
const trPosting = ref(false);

const transferDrawerTitle = computed(() =>
  transferDetail.value
    ? `Перемещение от ${formatDate(transferDetail.value.occurred_at)}`
    : "Перемещение",
);

async function openTransfer(row: { id: string }): Promise<void> {
  trDetailError.value = "";

  const { data, response } = await api.GET(
    "/api/inventory/transfers/{transfer_id}",
    { params: { path: { transfer_id: row.id } } },
  );

  if (!response.ok || !data) {
    notice.value = "Не удалось открыть перемещение";
    return;
  }

  transferDetail.value = data;
  transferDrawerOpen.value = true;
}

async function postTransfer(): Promise<void> {
  if (!transferDetail.value) {
    return;
  }

  trPosting.value = true;
  trDetailError.value = "";

  try {
    const { response } = await api.POST(
      "/api/inventory/transfers/{transfer_id}/post",
      { params: { path: { transfer_id: transferDetail.value.id } } },
    );

    if (!response.ok) {
      trDetailError.value = "Не удалось провести перемещение";
      return;
    }

    const transferId = transferDetail.value.id;
    await openTransfer({ id: transferId });
    await reload();
  } finally {
    trPosting.value = false;
  }
}

const trEditingId = ref<string | null>(null);

function openTransferEdit(): void {
  const detail = transferDetail.value;

  if (!detail) {
    return;
  }

  trError.value = "";
  notice.value = "";
  trEditingId.value = detail.id;
  trForm.from_org_unit_id = detail.from_org_unit_id;
  trForm.to_org_unit_id = detail.to_org_unit_id;
  trForm.occurred_at = new Date(detail.occurred_at);
  trForm.comment = detail.comment ?? "";
  trLines.value = detail.lines.map((line) => ({
    nomenclature_id: line.nomenclature_id,
    quantity: String(line.quantity),
    lot_code: line.lot_code ?? "",
    options: [
      {
        id: line.nomenclature_id,
        name: line.nomenclature_name ?? line.nomenclature_id,
        sku: "",
      },
    ],
  }));
  transferDrawerOpen.value = false;
  transferOpen.value = true;
}

type InventoryCountLine = {
  nomenclature_id: string;
  options: NomenclatureOption[];
  counted_quantity: string;
  lot_code: string;
};

function emptyInventoryCountLine(): InventoryCountLine {
  return { nomenclature_id: "", options: [], counted_quantity: "", lot_code: "" };
}

const icOpen = ref(false);
const icSaving = ref(false);
const icError = ref("");
const icEditingId = ref<string | null>(null);
const icForm = reactive({
  org_unit_id: "",
  occurred_at: new Date(),
  comment: "",
});
const icLines = ref<InventoryCountLine[]>([emptyInventoryCountLine()]);
const bookQuantities = ref<Record<string, string>>({});

function isCompleteInventoryCountLine(line: InventoryCountLine): boolean {
  return (
    Boolean(line.nomenclature_id) &&
    line.counted_quantity !== "" &&
    Number(line.counted_quantity) >= 0
  );
}

const icCanSubmit = computed(
  () =>
    Boolean(icForm.org_unit_id) &&
    icLines.value.some(isCompleteInventoryCountLine),
);

const icDrawerOpen = ref(false);
const inventoryCountDetail = ref<InventoryCountDetail | null>(null);
const icDetailError = ref("");
const icPosting = ref(false);

const icDrawerTitle = computed(() =>
  inventoryCountDetail.value
    ? `Инвентаризация от ${formatDate(inventoryCountDetail.value.occurred_at)}`
    : "Инвентаризация",
);

function bookQuantity(nomenclatureId: string): string {
  if (!nomenclatureId) {
    return "—";
  }

  const value = bookQuantities.value[nomenclatureId];

  return value === undefined ? "—" : formatQuantity(value);
}

async function loadBookQuantities(): Promise<void> {
  bookQuantities.value = {};

  if (!icForm.org_unit_id || !can("inventory.balance.read")) {
    return;
  }

  const { data, response } = await api.GET(
    "/api/inventory/locations/{org_unit_id}/balances",
    {
      params: {
        path: { org_unit_id: icForm.org_unit_id },
        query: { limit: 200 },
      },
    },
  );

  if (response.ok && data) {
    const map: Record<string, string> = {};
    for (const item of data.items) {
      map[item.nomenclature_id] = item.quantity;
    }
    bookQuantities.value = map;
  }
}

watch(
  () => icForm.org_unit_id,
  () => {
    void loadBookQuantities();
  },
);

function openInventoryCountCreate(): void {
  icEditingId.value = null;
  icError.value = "";
  notice.value = "";
  icForm.org_unit_id = locations.value[0]?.id ?? "";
  icForm.occurred_at = new Date();
  icForm.comment = "";
  icLines.value = [emptyInventoryCountLine()];
  bookQuantities.value = {};
  icOpen.value = true;
  void loadBookQuantities();
}

function addInventoryCountLine(): void {
  icLines.value = [...icLines.value, emptyInventoryCountLine()];
}

function removeInventoryCountLine(index: number): void {
  icLines.value = icLines.value.filter((_, position) => position !== index);
}

function inventoryCountBody() {
  return {
    occurred_at: icForm.occurred_at.toISOString(),
    comment: icForm.comment.trim() || null,
    lines: icLines.value
      .filter(isCompleteInventoryCountLine)
      .map((line) => ({
        nomenclature_id: line.nomenclature_id,
        counted_quantity: line.counted_quantity,
        lot_code: line.lot_code.trim() || null,
      })),
  };
}

async function saveInventoryCount(postAfterCreate: boolean): Promise<void> {
  if (icEditingId.value) {
    await updateInventoryCount();
    return;
  }

  icSaving.value = true;
  icError.value = "";
  notice.value = "";

  try {
    const created = await api.POST("/api/inventory/inventory-counts", {
      body: {
        org_unit_id: icForm.org_unit_id,
        ...inventoryCountBody(),
      },
    });

    if (!created.response.ok || !created.data) {
      throw new Error(
        serverMessage(
          created.error,
          `Не удалось сохранить: ${created.response.status}`,
        ),
      );
    }

    const countId = (created.data as unknown as { inventory_count_id: string })
      .inventory_count_id;

    if (postAfterCreate) {
      const posted = await api.POST(
        "/api/inventory/inventory-counts/{inventory_count_id}/post",
        { params: { path: { inventory_count_id: countId } } },
      );

      if (!posted.response.ok) {
        icError.value = `Черновик создан, но не проведён: ${serverMessage(posted.error, String(posted.response.status))}`;
        tab.value = "inventory-counts";
        await refresh();
        return;
      }

      notice.value = "Инвентаризация проведена";
    } else {
      notice.value = "Черновик инвентаризации сохранён";
    }

    icOpen.value = false;
    tab.value = "inventory-counts";
    await refresh();
  } catch (cause) {
    icError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    icSaving.value = false;
  }
}

async function updateInventoryCount(): Promise<void> {
  icSaving.value = true;
  icError.value = "";
  notice.value = "";

  try {
    const updated = await api.PATCH(
      "/api/inventory/inventory-counts/{inventory_count_id}",
      {
        params: { path: { inventory_count_id: icEditingId.value ?? "" } },
        body: inventoryCountBody(),
      },
    );

    if (!updated.response.ok) {
      throw new Error(
        serverMessage(
          updated.error,
          `Не удалось сохранить: ${updated.response.status}`,
        ),
      );
    }

    const editedId = icEditingId.value;
    icOpen.value = false;
    icEditingId.value = null;
    notice.value = "Изменения сохранены";
    if (editedId) {
      await openInventoryCount({ id: editedId });
    }
    await refresh();
  } catch (cause) {
    icError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    icSaving.value = false;
  }
}

async function openInventoryCount(row: { id: string }): Promise<void> {
  icDetailError.value = "";

  const { data, response } = await api.GET(
    "/api/inventory/inventory-counts/{inventory_count_id}",
    { params: { path: { inventory_count_id: row.id } } },
  );

  if (!response.ok || !data) {
    error.value = reasonOf(response.status, "Не удалось открыть инвентаризацию");
    return;
  }

  inventoryCountDetail.value = data;
  icDrawerOpen.value = true;
}

function openInventoryCountEdit(): void {
  const detail = inventoryCountDetail.value;

  if (!detail) {
    return;
  }

  icError.value = "";
  notice.value = "";
  icEditingId.value = detail.id;
  icForm.org_unit_id = detail.org_unit_id;
  icForm.occurred_at = new Date(detail.occurred_at);
  icForm.comment = detail.comment ?? "";
  icLines.value = detail.lines.map((line) => ({
    nomenclature_id: line.nomenclature_id,
    counted_quantity: String(line.counted_quantity),
    lot_code: line.lot_code ?? "",
    options: [
      {
        id: line.nomenclature_id,
        name: line.nomenclature_name ?? line.nomenclature_id,
        sku: "",
      },
    ],
  }));
  icDrawerOpen.value = false;
  icOpen.value = true;
  void loadBookQuantities();
}

async function postInventoryCount(id: string): Promise<void> {
  icPosting.value = true;
  icDetailError.value = "";
  error.value = "";
  notice.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/inventory/inventory-counts/{inventory_count_id}/post",
      { params: { path: { inventory_count_id: id } } },
    );

    if (!response.ok) {
      throw new Error(
        serverMessage(failure, `Не удалось провести: ${response.status}`),
      );
    }

    notice.value = "Инвентаризация проведена";

    if (icDrawerOpen.value) {
      await openInventoryCount({ id });
    }
    await refresh();
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : "Ошибка проведения";
    if (icDrawerOpen.value) {
      icDetailError.value = message;
    } else {
      error.value = message;
    }
  } finally {
    icPosting.value = false;
  }
}


function deleteReasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав удалять документы склада";
  }
  if (status === 404) {
    return "Документ не найден";
  }
  if (status === 409) {
    return "Проведённый документ удалить нельзя";
  }

  return `${fallback}: ${status}`;
}


async function deleteReceipt(row: { id: string }): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE("/api/inventory/receipts/{receipt_id}", {
      params: { path: { receipt_id: row.id } },
    });

    if (!response.ok) {
      throw new Error(
        deleteReasonOf(response.status, "Не удалось удалить поступление"),
      );
    }

    notice.value = "Черновик поступления удалён";
    receiptDetail.value = null;
    drawerOpen.value = false;
    await refresh();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка удаления";
  } finally {
    busy.value = false;
  }
}


async function deleteWriteOff(row: { id: string }): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE("/api/inventory/write-offs/{write_off_id}", {
      params: { path: { write_off_id: row.id } },
    });

    if (!response.ok) {
      throw new Error(
        deleteReasonOf(response.status, "Не удалось удалить списание"),
      );
    }

    notice.value = "Черновик списания удалён";
    writeOffDetail.value = null;
    drawerOpen.value = false;
    await refresh();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка удаления";
  } finally {
    busy.value = false;
  }
}


async function deleteTransfer(row: { id: string }): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE("/api/inventory/transfers/{transfer_id}", {
      params: { path: { transfer_id: row.id } },
    });

    if (!response.ok) {
      throw new Error(
        deleteReasonOf(response.status, "Не удалось удалить перемещение"),
      );
    }

    notice.value = "Черновик перемещения удалён";
    transferDetail.value = null;
    transferDrawerOpen.value = false;
    await refresh();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка удаления";
  } finally {
    busy.value = false;
  }
}


async function deleteInventoryCount(id: string): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE(
      "/api/inventory/inventory-counts/{inventory_count_id}",
      { params: { path: { inventory_count_id: id } } },
    );

    if (!response.ok) {
      throw new Error(
        deleteReasonOf(response.status, "Не удалось удалить инвентаризацию"),
      );
    }

    notice.value = "Черновик инвентаризации удалён";
    inventoryCountDetail.value = null;
    icDrawerOpen.value = false;
    await refresh();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка удаления";
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.page__error {
  margin-bottom: 16px;
}

.pager {
  margin-top: 18px;
  justify-content: flex-end;
}

.lines {
  margin-top: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.lines-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 8px 0;
  font-weight: 600;
}

.line {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.line__name {
  flex: 1;
}

.line__qty {
  width: 110px;
}

.line__qty--book {
  text-align: right;
  padding-right: 8px;
  color: #606266;
}

.line__lot {
  width: 130px;
}

.line__date {
  width: 150px;
}

.line__action {
  width: 74px;
}

.line--write-off .line__name {
  flex: 1;
}

.line--head {
  color: #909399;
  font-size: 12px;
  margin-bottom: 4px;
}

.hint {
  font-size: 11px;
}
</style>
