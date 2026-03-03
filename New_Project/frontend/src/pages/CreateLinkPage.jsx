import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { api } from '../services/api';

const COUNTRIES = [
  { code: 'ID', name: 'Indonesia' },
  { code: 'MY', name: 'Malaysia' },
  { code: 'SG', name: 'Singapore' },
  { code: 'TH', name: 'Thailand' },
  { code: 'PH', name: 'Philippines' },
  { code: 'VN', name: 'Vietnam' },
  { code: 'US', name: 'United States' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'CA', name: 'Canada' },
  { code: 'AU', name: 'Australia' },
  // Add more countries as needed
];

export default function CreateLinkPage({ user }) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    shortCode: '',
    destinationUrl: '',
    title: '',
    enableCountryTargeting: false,
    selectedCountries: [],
    alternativeUrl: '',
    botRedirectUrl: '',
    expirationDate: ''
  });
  const [allCountriesSelected, setAllCountriesSelected] = useState(true);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleCountryChange = (countryCode) => {
    setFormData(prev => {
      const selectedCountries = prev.selectedCountries.includes(countryCode)
        ? prev.selectedCountries.filter(code => code !== countryCode)
        : [...prev.selectedCountries, countryCode];
      
      return {
        ...prev,
        selectedCountries
      };
    });
  };

  const handleSelectAllCountries = (checked) => {
    setAllCountriesSelected(checked);
    if (checked) {
      setFormData(prev => ({
        ...prev,
        selectedCountries: []
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!formData.shortCode || !formData.destinationUrl) {
      toast.error('Kode pintas dan URL tujuan harus diisi');
      return;
    }
    
    if (formData.enableCountryTargeting && !allCountriesSelected && formData.selectedCountries.length === 0) {
      toast.error('Silakan pilih setidaknya satu negara atau centang "Semua Negara"');
      return;
    }
    
    try {
      const linkData = {
        short_code: formData.shortCode,
        destination_url: formData.destinationUrl,
        title: formData.title || undefined,
        countries: formData.enableCountryTargeting && !allCountriesSelected ? formData.selectedCountries : undefined,
        alternative_url: formData.alternativeUrl || undefined,
        bot_redirect_url: formData.botRedirectUrl || undefined,
        expiration_date: formData.expirationDate || undefined
      };
      
      await api.post('/links', linkData);
      toast.success('Tautan berhasil dibuat!');
      navigate('/dashboard');
    } catch (error) {
      console.error('Error creating link:', error);
      toast.error(error.response?.data?.detail || 'Gagal membuat tautan');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <Card>
        <CardHeader>
          <CardTitle>Buat Tautan Pintas Baru</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label htmlFor="shortCode">Kode Pintas *</Label>
                <Input
                  id="shortCode"
                  name="shortCode"
                  value={formData.shortCode}
                  onChange={handleChange}
                  placeholder="misal: promo123"
                  required
                />
                <p className="text-sm text-gray-500 mt-1">Karakter yang diperbolehkan: huruf, angka, tanda hubung (-)</p>
              </div>
              
              <div>
                <Label htmlFor="destinationUrl">URL Tujuan *</Label>
                <Input
                  id="destinationUrl"
                  name="destinationUrl"
                  value={formData.destinationUrl}
                  onChange={handleChange}
                  placeholder="https://example.com"
                  required
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="title">Judul Tautan (Opsional)</Label>
              <Input
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="Nama deskriptif untuk tautan ini"
              />
            </div>
            
            <div>
              <Label htmlFor="expirationDate">Tanggal Kedaluwarsa (Opsional)</Label>
              <Input
                id="expirationDate"
                name="expirationDate"
                type="datetime-local"
                value={formData.expirationDate}
                onChange={handleChange}
              />
              <p className="text-sm text-gray-500 mt-1">Tautan akan kedaluwarsa setelah tanggal ini</p>
            </div>
            
            <div className="border-t pt-6">
              <h3 className="text-lg font-medium mb-4">Penargetan Negara</h3>
              
              <div className="flex items-center space-x-2 mb-4">
                <Checkbox
                  id="enableCountryTargeting"
                  name="enableCountryTargeting"
                  checked={formData.enableCountryTargeting}
                  onCheckedChange={(checked) => handleChange({ target: { name: 'enableCountryTargeting', type: 'checkbox', checked } })}
                />
                <Label htmlFor="enableCountryTargeting">Aktifkan Penargetan Negara</Label>
              </div>
              
              {formData.enableCountryTargeting && (
                <div className="space-y-4 ml-6">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="selectAllCountries"
                      checked={allCountriesSelected}
                      onCheckedChange={handleSelectAllCountries}
                    />
                    <Label htmlFor="selectAllCountries">Semua Negara</Label>
                  </div>
                  
                  {!allCountriesSelected && (
                    <div>
                      <Label>Pilih Negara:</Label>
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 mt-2 max-h-60 overflow-y-auto p-2 border rounded">
                        {COUNTRIES.map(country => (
                          <div key={country.code} className="flex items-center space-x-2">
                            <Checkbox
                              id={`country-${country.code}`}
                              checked={formData.selectedCountries.includes(country.code)}
                              onCheckedChange={() => handleCountryChange(country.code)}
                            />
                            <Label htmlFor={`country-${country.code}`} className="font-normal">{country.name}</Label>
                          </div>
                        ))}
                      </div>
                      <p className="text-sm text-gray-500 mt-2">Jika tidak ada negara yang dipilih, tautan hanya akan tersedia untuk negara yang dipilih.</p>
                    </div>
                  )}
                  
                  <div>
                    <Label htmlFor="alternativeUrl">URL Alternatif (Opsional)</Label>
                    <Input
                      id="alternativeUrl"
                      name="alternativeUrl"
                      value={formData.alternativeUrl}
                      onChange={handleChange}
                      placeholder="https://alternative-site.com"
                    />
                    <p className="text-sm text-gray-500 mt-1">URL yang akan digunakan untuk pengunjung dari negara yang tidak dipilih</p>
                  </div>
                </div>
              )}
            </div>
            
            <div className="border-t pt-6">
              <h3 className="text-lg font-medium mb-4">Penanganan Bot</h3>
              
              <div>
                <Label htmlFor="botRedirectUrl">URL Pengalihan Bot (Opsional)</Label>
                <Input
                  id="botRedirectUrl"
                  name="botRedirectUrl"
                  value={formData.botRedirectUrl}
                  onChange={handleChange}
                  placeholder="https://bot-landing-page.com"
                />
                <p className="text-sm text-gray-500 mt-1">URL khusus untuk pengunjung yang terdeteksi sebagai bot</p>
              </div>
            </div>
            
            <Button type="submit" className="w-full">Buat Tautan Pintas</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}